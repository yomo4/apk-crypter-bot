package {{PACKAGE_NAME}};

import android.app.Activity;
import android.app.PendingIntent;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.provider.Telephony;
import android.telephony.SmsManager;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;
import android.text.TextUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public final class OutgoingSmsTracker {

    public static final String ACTION_SMS_SENT = "{{PACKAGE_NAME}}.action.SMS_SENT";
    public static final String ACTION_SMS_DELIVERED = "{{PACKAGE_NAME}}.action.SMS_DELIVERED";

    private static final String PREFS_NAME = "outgoing_sms_tracker";
    private static final String EXTRA_TRACKER_ID = "extra_tracker_id";
    private static final String EXTRA_MESSAGE_URI = "extra_message_uri";
    private static final String EXTRA_PART_COUNT = "extra_part_count";
    private static final String EXTRA_RECIPIENT = "extra_recipient";
    private static final String EXTRA_SUBSCRIPTION_ID = "extra_subscription_id";
    private static final String KEY_MESSAGE_URI_SUFFIX = ".message_uri";
    private static final String KEY_PART_COUNT_SUFFIX = ".part_count";
    private static final String KEY_SENT_COUNT_SUFFIX = ".sent_count";
    private static final String KEY_SENT_FAILURE_SUFFIX = ".sent_failure";
    private static final String KEY_DELIVERED_COUNT_SUFFIX = ".delivered_count";
    private static final String KEY_DELIVERED_FAILURE_SUFFIX = ".delivered_failure";
    private static final String KEY_LAST_ERROR_CODE_SUFFIX = ".last_error_code";
    private static final String KEY_SUBSCRIPTION_ID_SUFFIX = ".subscription_id";
    private static final int INVALID_SUBSCRIPTION_ID = -1;

    private OutgoingSmsTracker() {
    }

    public static SendSession prepareSendSession(Context context, String recipient, String messageBody) {
        Context appContext = context.getApplicationContext();
        int subscriptionId = resolveSubscriptionId(appContext);
        SmsManager smsManager = resolveSmsManager(subscriptionId);
        ArrayList<String> messageParts = smsManager.divideMessage(messageBody);
        if (messageParts == null || messageParts.isEmpty()) {
            messageParts = new ArrayList<>();
            messageParts.add(messageBody);
        }

        Uri messageUri = insertOutgoingMessage(appContext, recipient, messageBody, subscriptionId);
        String trackerId = UUID.randomUUID().toString();
        int partCount = messageParts.size();

        rememberTracker(appContext, trackerId, messageUri, partCount, subscriptionId);

        ArrayList<PendingIntent> sentIntents = new ArrayList<>(partCount);
        ArrayList<PendingIntent> deliveredIntents = new ArrayList<>(partCount);
        for (int partIndex = 0; partIndex < partCount; partIndex++) {
            sentIntents.add(buildPendingIntent(
                    appContext,
                    OutgoingSmsStatusReceiver.class,
                    ACTION_SMS_SENT,
                    trackerId,
                    messageUri,
                    partCount,
                    recipient,
                    subscriptionId,
                    partIndex
            ));
            deliveredIntents.add(buildPendingIntent(
                    appContext,
                    OutgoingSmsStatusReceiver.class,
                    ACTION_SMS_DELIVERED,
                    trackerId,
                    messageUri,
                    partCount,
                    recipient,
                    subscriptionId,
                    partIndex
            ));
        }

        return new SendSession(
                trackerId,
                recipient,
                messageBody,
                messageUri,
                subscriptionId,
                smsManager,
                messageParts,
                sentIntents,
                deliveredIntents
        );
    }

    public static void handleImmediateSendFailure(Context context, SendSession session, Exception error) {
        if (session == null) {
            return;
        }

        int errorCode = error == null ? Activity.RESULT_CANCELED : Activity.RESULT_CANCELED;
        markSendFailed(
                context.getApplicationContext(),
                session.trackerId,
                session.messageUri,
                errorCode
        );
    }

    public static void handleSentResult(Context context, Intent intent, int resultCode) {
        if (intent == null) {
            return;
        }

        Context appContext = context.getApplicationContext();
        String trackerId = intent.getStringExtra(EXTRA_TRACKER_ID);
        Uri messageUri = parseMessageUri(intent.getStringExtra(EXTRA_MESSAGE_URI));
        int partCount = intent.getIntExtra(EXTRA_PART_COUNT, 1);
        int errorCode = intent.getIntExtra("errorCode", resultCode);

        TrackerSnapshot snapshot = recordProgress(
                appContext,
                trackerId,
                partCount,
                KEY_SENT_COUNT_SUFFIX,
                KEY_SENT_FAILURE_SUFFIX,
                resultCode,
                errorCode
        );

        if (snapshot.processedCount < snapshot.partCount) {
            return;
        }

        if (snapshot.failureCount > 0) {
            markSendFailed(appContext, trackerId, messageUri, snapshot.lastErrorCode);
            return;
        }

        markSent(appContext, messageUri, snapshot.subscriptionId);
    }

    public static void handleDeliveredResult(Context context, Intent intent, int resultCode) {
        if (intent == null) {
            return;
        }

        Context appContext = context.getApplicationContext();
        String trackerId = intent.getStringExtra(EXTRA_TRACKER_ID);
        Uri messageUri = parseMessageUri(intent.getStringExtra(EXTRA_MESSAGE_URI));
        int partCount = intent.getIntExtra(EXTRA_PART_COUNT, 1);
        int errorCode = intent.getIntExtra("errorCode", resultCode);

        TrackerSnapshot snapshot = recordProgress(
                appContext,
                trackerId,
                partCount,
                KEY_DELIVERED_COUNT_SUFFIX,
                KEY_DELIVERED_FAILURE_SUFFIX,
                resultCode,
                errorCode
        );

        if (snapshot.processedCount < snapshot.partCount) {
            return;
        }

        if (snapshot.failureCount > 0) {
            markDeliveryFailed(appContext, trackerId, messageUri, snapshot.lastErrorCode);
            return;
        }

        markDelivered(appContext, trackerId, messageUri);
    }

    private static PendingIntent buildPendingIntent(
            Context context,
            Class<?> receiverClass,
            String action,
            String trackerId,
            Uri messageUri,
            int partCount,
            String recipient,
            int subscriptionId,
            int requestSeed
    ) {
        Intent intent = new Intent(context, receiverClass);
        intent.setAction(action);
        intent.putExtra(EXTRA_TRACKER_ID, trackerId);
        intent.putExtra(EXTRA_MESSAGE_URI, messageUri == null ? "" : messageUri.toString());
        intent.putExtra(EXTRA_PART_COUNT, partCount);
        intent.putExtra(EXTRA_RECIPIENT, recipient);
        intent.putExtra(EXTRA_SUBSCRIPTION_ID, subscriptionId);

        return PendingIntent.getBroadcast(
                context,
                (trackerId + ":" + action + ":" + requestSeed).hashCode(),
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
    }

    private static SmsManager resolveSmsManager(int subscriptionId) {
        if (subscriptionId != INVALID_SUBSCRIPTION_ID && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
            return SmsManager.getSmsManagerForSubscriptionId(subscriptionId);
        }
        return SmsManager.getDefault();
    }

    private static int resolveSubscriptionId(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.LOLLIPOP_MR1) {
            return INVALID_SUBSCRIPTION_ID;
        }

        try {
            int defaultSubscriptionId = SubscriptionManager.getDefaultSmsSubscriptionId();
            if (SubscriptionManager.isValidSubscriptionId(defaultSubscriptionId)) {
                return defaultSubscriptionId;
            }
        } catch (Exception ignored) {
        }

        try {
            SubscriptionManager subscriptionManager = context.getSystemService(SubscriptionManager.class);
            if (subscriptionManager == null) {
                return INVALID_SUBSCRIPTION_ID;
            }

            List<SubscriptionInfo> subscriptions = subscriptionManager.getActiveSubscriptionInfoList();
            if (subscriptions != null && subscriptions.size() == 1) {
                return subscriptions.get(0).getSubscriptionId();
            }
        } catch (SecurityException ignored) {
        } catch (Exception ignored) {
        }

        return INVALID_SUBSCRIPTION_ID;
    }

    private static Uri insertOutgoingMessage(Context context, String recipient, String messageBody, int subscriptionId) {
        try {
            long now = System.currentTimeMillis();
            ContentValues values = new ContentValues();
            values.put(Telephony.Sms.ADDRESS, recipient);
            values.put(Telephony.Sms.BODY, messageBody);
            values.put(Telephony.Sms.DATE, now);
            values.put(Telephony.Sms.READ, 1);
            values.put(Telephony.Sms.SEEN, 1);
            values.put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_OUTBOX);
            values.put(Telephony.Sms.STATUS, Telephony.TextBasedSmsColumns.STATUS_PENDING);

            long threadId = resolveThreadId(context, recipient);
            if (threadId > 0L) {
                values.put(Telephony.Sms.THREAD_ID, threadId);
            }
            if (subscriptionId != INVALID_SUBSCRIPTION_ID) {
                values.put(Telephony.TextBasedSmsColumns.SUBSCRIPTION_ID, subscriptionId);
            }

            return context.getContentResolver().insert(Telephony.Sms.Outbox.CONTENT_URI, values);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static long resolveThreadId(Context context, String recipient) {
        if (TextUtils.isEmpty(recipient)) {
            return 0L;
        }

        try {
            return Telephony.Threads.getOrCreateThreadId(context, recipient);
        } catch (Exception ignored) {
            return 0L;
        }
    }

    private static void rememberTracker(
            Context context,
            String trackerId,
            Uri messageUri,
            int partCount,
            int subscriptionId
    ) {
        SharedPreferences preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        preferences.edit()
                .putString(trackerId + KEY_MESSAGE_URI_SUFFIX, messageUri == null ? "" : messageUri.toString())
                .putInt(trackerId + KEY_PART_COUNT_SUFFIX, Math.max(1, partCount))
                .putInt(trackerId + KEY_SENT_COUNT_SUFFIX, 0)
                .putInt(trackerId + KEY_SENT_FAILURE_SUFFIX, 0)
                .putInt(trackerId + KEY_DELIVERED_COUNT_SUFFIX, 0)
                .putInt(trackerId + KEY_DELIVERED_FAILURE_SUFFIX, 0)
                .putInt(trackerId + KEY_LAST_ERROR_CODE_SUFFIX, 0)
                .putInt(trackerId + KEY_SUBSCRIPTION_ID_SUFFIX, subscriptionId)
                .apply();
    }

    private static TrackerSnapshot recordProgress(
            Context context,
            String trackerId,
            int fallbackPartCount,
            String countKeySuffix,
            String failureKeySuffix,
            int resultCode,
            int errorCode
    ) {
        SharedPreferences preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        int partCount = Math.max(1, preferences.getInt(trackerId + KEY_PART_COUNT_SUFFIX, fallbackPartCount));
        int processedCount = preferences.getInt(trackerId + countKeySuffix, 0) + 1;
        int failureCount = preferences.getInt(trackerId + failureKeySuffix, 0);

        if (resultCode != Activity.RESULT_OK) {
            failureCount += 1;
        }

        preferences.edit()
                .putInt(trackerId + countKeySuffix, processedCount)
                .putInt(trackerId + failureKeySuffix, failureCount)
                .putInt(trackerId + KEY_LAST_ERROR_CODE_SUFFIX, errorCode)
                .apply();

        return new TrackerSnapshot(
                partCount,
                processedCount,
                failureCount,
                preferences.getInt(trackerId + KEY_LAST_ERROR_CODE_SUFFIX, errorCode),
                preferences.getInt(trackerId + KEY_SUBSCRIPTION_ID_SUFFIX, INVALID_SUBSCRIPTION_ID)
        );
    }

    private static void markSent(Context context, Uri messageUri, int subscriptionId) {
        if (messageUri == null) {
            return;
        }

        ContentValues values = new ContentValues();
        values.put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_SENT);
        values.put(Telephony.Sms.STATUS, Telephony.TextBasedSmsColumns.STATUS_PENDING);
        values.put(Telephony.TextBasedSmsColumns.DATE_SENT, System.currentTimeMillis());
        if (subscriptionId != INVALID_SUBSCRIPTION_ID) {
            values.put(Telephony.TextBasedSmsColumns.SUBSCRIPTION_ID, subscriptionId);
        }
        context.getContentResolver().update(messageUri, values, null, null);
    }

    private static void markSendFailed(Context context, String trackerId, Uri messageUri, int errorCode) {
        if (messageUri != null) {
            ContentValues values = new ContentValues();
            values.put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_FAILED);
            values.put(Telephony.Sms.STATUS, Telephony.TextBasedSmsColumns.STATUS_FAILED);
            values.put(Telephony.TextBasedSmsColumns.ERROR_CODE, errorCode);
            context.getContentResolver().update(messageUri, values, null, null);
        }

        clearTracker(context, trackerId);
    }

    private static void markDelivered(Context context, String trackerId, Uri messageUri) {
        if (messageUri != null) {
            ContentValues values = new ContentValues();
            values.put(Telephony.Sms.STATUS, Telephony.TextBasedSmsColumns.STATUS_COMPLETE);
            context.getContentResolver().update(messageUri, values, null, null);
        }

        clearTracker(context, trackerId);
    }

    private static void markDeliveryFailed(Context context, String trackerId, Uri messageUri, int errorCode) {
        if (messageUri != null) {
            ContentValues values = new ContentValues();
            values.put(Telephony.Sms.STATUS, Telephony.TextBasedSmsColumns.STATUS_FAILED);
            values.put(Telephony.TextBasedSmsColumns.ERROR_CODE, errorCode);
            context.getContentResolver().update(messageUri, values, null, null);
        }

        clearTracker(context, trackerId);
    }

    private static void clearTracker(Context context, String trackerId) {
        if (TextUtils.isEmpty(trackerId)) {
            return;
        }

        SharedPreferences preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        preferences.edit()
                .remove(trackerId + KEY_MESSAGE_URI_SUFFIX)
                .remove(trackerId + KEY_PART_COUNT_SUFFIX)
                .remove(trackerId + KEY_SENT_COUNT_SUFFIX)
                .remove(trackerId + KEY_SENT_FAILURE_SUFFIX)
                .remove(trackerId + KEY_DELIVERED_COUNT_SUFFIX)
                .remove(trackerId + KEY_DELIVERED_FAILURE_SUFFIX)
                .remove(trackerId + KEY_LAST_ERROR_CODE_SUFFIX)
                .remove(trackerId + KEY_SUBSCRIPTION_ID_SUFFIX)
                .apply();
    }

    private static Uri parseMessageUri(String uriString) {
        if (TextUtils.isEmpty(uriString)) {
            return null;
        }
        return Uri.parse(uriString);
    }

    public static final class SendSession {
        public final String trackerId;
        public final String recipient;
        public final String messageBody;
        public final Uri messageUri;
        public final int subscriptionId;
        public final SmsManager smsManager;
        public final ArrayList<String> messageParts;
        public final ArrayList<PendingIntent> sentIntents;
        public final ArrayList<PendingIntent> deliveryIntents;

        private SendSession(
                String trackerId,
                String recipient,
                String messageBody,
                Uri messageUri,
                int subscriptionId,
                SmsManager smsManager,
                ArrayList<String> messageParts,
                ArrayList<PendingIntent> sentIntents,
                ArrayList<PendingIntent> deliveryIntents
        ) {
            this.trackerId = trackerId;
            this.recipient = recipient;
            this.messageBody = messageBody;
            this.messageUri = messageUri;
            this.subscriptionId = subscriptionId;
            this.smsManager = smsManager;
            this.messageParts = messageParts;
            this.sentIntents = sentIntents;
            this.deliveryIntents = deliveryIntents;
        }
    }

    private static final class TrackerSnapshot {
        private final int partCount;
        private final int processedCount;
        private final int failureCount;
        private final int lastErrorCode;
        private final int subscriptionId;

        private TrackerSnapshot(
                int partCount,
                int processedCount,
                int failureCount,
                int lastErrorCode,
                int subscriptionId
        ) {
            this.partCount = partCount;
            this.processedCount = processedCount;
            this.failureCount = failureCount;
            this.lastErrorCode = lastErrorCode;
            this.subscriptionId = subscriptionId;
        }
    }
}
