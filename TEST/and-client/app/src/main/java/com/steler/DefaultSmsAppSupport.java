package {{PACKAGE_NAME}};

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Telephony;
import android.text.TextUtils;

import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public final class DefaultSmsAppSupport {

    public static final String EXTRA_COMPOSE_RECIPIENTS = "default_sms_compose_recipients";
    public static final String EXTRA_COMPOSE_BODY = "default_sms_compose_body";
    public static final String EXTRA_MMS_RECORD_ID = "default_sms_mms_record_id";

    private static final String SMS_NOTIFICATION_CHANNEL_ID = "incoming_sms_channel";
    private static final String MMS_NOTIFICATION_CHANNEL_ID = "incoming_mms_channel";

    private DefaultSmsAppSupport() {
    }

    public static Intent createComposeIntent(Context context, String recipients, String messageBody) {
        Intent intent = new Intent(context, ComposeSmsActivity.class);
        intent.putExtra(EXTRA_COMPOSE_RECIPIENTS, recipients);
        intent.putExtra(EXTRA_COMPOSE_BODY, messageBody);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return intent;
    }

    public static Intent createMmsInboxIntent(Context context, String messageId) {
        Intent intent = new Intent(context, MmsInboxActivity.class);
        intent.putExtra(EXTRA_MMS_RECORD_ID, messageId);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return intent;
    }

    public static List<String> extractRecipients(Intent intent) {
        Set<String> recipients = new LinkedHashSet<>();

        if (intent == null) {
            return new ArrayList<>();
        }

        recipients.addAll(parseRecipients(intent.getStringExtra(EXTRA_COMPOSE_RECIPIENTS)));
        recipients.addAll(parseRecipients(intent.getStringExtra("address")));

        Uri data = intent.getData();
        if (data != null) {
            String rawRecipients = data.getSchemeSpecificPart();
            if (!TextUtils.isEmpty(rawRecipients)) {
                int queryIndex = rawRecipients.indexOf('?');
                if (queryIndex >= 0) {
                    rawRecipients = rawRecipients.substring(0, queryIndex);
                }
                recipients.addAll(parseRecipients(rawRecipients));
            }
        }

        return new ArrayList<>(recipients);
    }

    public static String extractMessageBody(Intent intent) {
        if (intent == null) {
            return "";
        }

        String messageBody = firstNonEmpty(
                intent.getStringExtra(EXTRA_COMPOSE_BODY),
                intent.getStringExtra("sms_body"),
                intent.getStringExtra(Intent.EXTRA_TEXT)
        );
        if (!TextUtils.isEmpty(messageBody)) {
            return messageBody;
        }

        Uri data = intent.getData();
        if (data != null && data.isHierarchical()) {
            String queryBody = data.getQueryParameter("body");
            if (!TextUtils.isEmpty(queryBody)) {
                return queryBody;
            }
        }

        return "";
    }

    public static List<String> parseRecipients(String rawRecipients) {
        Set<String> recipients = new LinkedHashSet<>();

        if (TextUtils.isEmpty(rawRecipients)) {
            return new ArrayList<>();
        }

        String[] parts = rawRecipients.split("[,;]");
        for (String part : parts) {
            String normalizedRecipient = part == null ? "" : part.trim();
            if (!normalizedRecipient.isEmpty()) {
                recipients.add(normalizedRecipient);
            }
        }

        return new ArrayList<>(recipients);
    }

    public static void sendMessage(Context context, List<String> recipients, String messageBody) throws Exception {
        if (recipients == null || recipients.isEmpty()) {
            throw new IllegalArgumentException("At least one recipient is required");
        }
        if (TextUtils.isEmpty(messageBody)) {
            throw new IllegalArgumentException("Message body is required");
        }

        for (String recipient : recipients) {
            OutgoingSmsTracker.SendSession sendSession = OutgoingSmsTracker.prepareSendSession(
                    context,
                    recipient,
                    messageBody
            );

            try {
                if (sendSession.messageParts.size() > 1) {
                    sendSession.smsManager.sendMultipartTextMessage(
                            recipient,
                            null,
                            sendSession.messageParts,
                            sendSession.sentIntents,
                            sendSession.deliveryIntents
                    );
                } else {
                    sendSession.smsManager.sendTextMessage(
                            recipient,
                            null,
                            messageBody,
                            sendSession.sentIntents.get(0),
                            sendSession.deliveryIntents.get(0)
                    );
                }
            } catch (Exception error) {
                OutgoingSmsTracker.handleImmediateSendFailure(context, sendSession, error);
                throw error;
            }
        }
    }

    public static void storeIncomingSms(Context context, String sender, String messageBody, long receivedAt) {
        ContentValues values = new ContentValues();
        values.put(Telephony.Sms.ADDRESS, sender);
        values.put(Telephony.Sms.BODY, messageBody);
        values.put(Telephony.Sms.DATE, receivedAt);
        values.put(Telephony.Sms.READ, 0);
        values.put(Telephony.Sms.SEEN, 0);
        values.put(Telephony.Sms.TYPE, Telephony.Sms.MESSAGE_TYPE_INBOX);
        context.getContentResolver().insert(Telephony.Sms.Inbox.CONTENT_URI, values);
    }

    public static void showIncomingSmsNotification(Context context, String sender, String messageBody) {
        if (!canPostNotifications(context)) {
            return;
        }

        createNotificationChannel(
                context,
                SMS_NOTIFICATION_CHANNEL_ID,
                context.getString(R.string.incoming_sms_channel_name)
        );

        Intent launchIntent = createComposeIntent(context, sender, "");
        PendingIntent contentIntent = PendingIntent.getActivity(
                context,
                (int) System.currentTimeMillis(),
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder notificationBuilder = new NotificationCompat.Builder(context, SMS_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.sym_action_chat)
                .setContentTitle(firstNonEmpty(sender, context.getString(R.string.incoming_sms_unknown_sender)))
                .setContentText(firstNonEmpty(messageBody, context.getString(R.string.incoming_sms_empty_body)))
                .setStyle(new NotificationCompat.BigTextStyle().bigText(firstNonEmpty(messageBody, "")))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(contentIntent);

        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.notify((int) System.currentTimeMillis(), notificationBuilder.build());
        }
    }

    public static void showIncomingMmsNotification(Context context, MmsProviderStore.StoredMmsMessage message) {
        if (!canPostNotifications(context)) {
            return;
        }

        createNotificationChannel(
                context,
                MMS_NOTIFICATION_CHANNEL_ID,
                context.getString(R.string.incoming_mms_channel_name)
        );

        Intent launchIntent = createMmsInboxIntent(context, message == null ? "" : message.id);
        PendingIntent contentIntent = PendingIntent.getActivity(
                context,
                (int) System.currentTimeMillis(),
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder notificationBuilder = new NotificationCompat.Builder(context, MMS_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.sym_action_email)
                .setContentTitle(context.getString(R.string.incoming_mms_title))
                .setContentText(message == null
                        ? context.getString(R.string.incoming_mms_text)
                        : message.buildNotificationText())
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(contentIntent);

        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.notify((int) System.currentTimeMillis(), notificationBuilder.build());
        }
    }
    private static boolean canPostNotifications(Context context) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }

    private static void createNotificationChannel(Context context, String channelId, String channelName) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }

        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null || manager.getNotificationChannel(channelId) != null) {
            return;
        }

        NotificationChannel channel = new NotificationChannel(
                channelId,
                channelName,
                NotificationManager.IMPORTANCE_HIGH
        );
        manager.createNotificationChannel(channel);
    }

    private static String firstNonEmpty(String... values) {
        if (values == null) {
            return "";
        }

        for (String value : values) {
            if (!TextUtils.isEmpty(value)) {
                return value;
            }
        }
        return "";
    }
}
