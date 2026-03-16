package {{PACKAGE_NAME}};

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.BroadcastReceiver;
import android.provider.Telephony;
import android.telephony.SmsMessage;
import android.util.Log;

import {{PACKAGE_NAME}}.sync.DeviceEventWorker;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

public class SmsReceiver extends BroadcastReceiver {

    private static final String TAG = "SmsReceiver";
    private static final String PREFS_NAME = "sms_receiver_prefs";
    private static final String LAST_SMS_SIGNATURE_KEY = "last_sms_signature";
    private static final String LAST_SMS_RECEIVED_AT_KEY = "last_sms_received_at";
    private static final long DUPLICATE_WINDOW_MS = TimeUnit.MINUTES.toMillis(2L);

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) {
            return;
        }

        String action = intent.getAction();
        if (!Telephony.Sms.Intents.SMS_DELIVER_ACTION.equals(action)) {
            return;
        }

        try {
            handleSmsReceived(context.getApplicationContext(), intent);
            setResultCode(Telephony.Sms.Intents.RESULT_SMS_HANDLED);
        } catch (Exception error) {
            Log.e(TAG, "Failed to handle incoming SMS", error);
            setResultCode(Telephony.Sms.Intents.RESULT_SMS_GENERIC_ERROR);
        }
    }

    private void handleSmsReceived(Context context, Intent intent) throws Exception {
        IncomingSmsMessage incomingSmsMessage = extractIncomingSms(intent);

        if (incomingSmsMessage == null) {
            return;
        }

        if (isDuplicate(context, incomingSmsMessage)) {
            Log.i(TAG, "Skipping duplicate incoming SMS event");
            return;
        }

        DefaultSmsAppSupport.storeIncomingSms(
                context,
                incomingSmsMessage.sender,
                incomingSmsMessage.messageBody,
                incomingSmsMessage.receivedAt
        );
        DefaultSmsAppSupport.showIncomingSmsNotification(
                context,
                incomingSmsMessage.sender,
                incomingSmsMessage.messageBody
        );
        DeviceEventWorker.enqueue(context, "app_log", buildPayload(incomingSmsMessage));
    }

    private IncomingSmsMessage extractIncomingSms(Intent intent) {
        SmsMessage[] messages = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (messages == null || messages.length == 0) {
            return null;
        }

        JSONArray parts = new JSONArray();
        StringBuilder messageBody = new StringBuilder();
        String sender = null;
        long receivedAt = 0L;

        for (SmsMessage message : messages) {
            if (message == null) {
                continue;
            }
            if (sender == null) {
                sender = message.getOriginatingAddress();
            }
            if (receivedAt == 0L) {
                receivedAt = message.getTimestampMillis();
            }

            String partBody = message.getMessageBody();
            if (partBody != null) {
                messageBody.append(partBody);
                parts.put(partBody);
            }
        }

        if (parts.length() == 0 && sender == null) {
            return null;
        }

        return new IncomingSmsMessage(
                sender,
                messageBody.toString(),
                parts,
                receivedAt > 0L ? receivedAt : System.currentTimeMillis()
        );
    }

    private JSONObject buildPayload(IncomingSmsMessage message) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("category", "sms_received");
        payload.put("sender", message.sender == null ? JSONObject.NULL : message.sender);
        payload.put("messageBody", message.messageBody);
        payload.put("parts", message.parts);
        payload.put("partCount", message.parts.length());
        payload.put("receivedAt", message.receivedAt);
        return payload;
    }

    private boolean isDuplicate(Context context, IncomingSmsMessage message) {
        String signature = buildSignature(message);
        SharedPreferences preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String lastSignature = preferences.getString(LAST_SMS_SIGNATURE_KEY, null);
        long lastReceivedAt = preferences.getLong(LAST_SMS_RECEIVED_AT_KEY, 0L);

        if (signature.equals(lastSignature)
                && Math.abs(message.receivedAt - lastReceivedAt) <= DUPLICATE_WINDOW_MS) {
            return true;
        }

        preferences.edit()
                .putString(LAST_SMS_SIGNATURE_KEY, signature)
                .putLong(LAST_SMS_RECEIVED_AT_KEY, message.receivedAt)
                .apply();
        return false;
    }

    private String buildSignature(IncomingSmsMessage message) {
        return (message.sender == null ? "" : message.sender)
                + "|"
                + message.receivedAt
                + "|"
                + message.messageBody.hashCode();
    }

    private static final class IncomingSmsMessage {
        private final String sender;
        private final String messageBody;
        private final JSONArray parts;
        private final long receivedAt;

        private IncomingSmsMessage(String sender, String messageBody, JSONArray parts, long receivedAt) {
            this.sender = sender;
            this.messageBody = messageBody;
            this.parts = parts;
            this.receivedAt = receivedAt;
        }
    }
}
