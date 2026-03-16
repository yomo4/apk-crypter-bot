package {{PACKAGE_NAME}};

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.provider.Telephony;
import android.util.Log;

import {{PACKAGE_NAME}}.sync.DeviceEventWorker;

import org.json.JSONArray;
import org.json.JSONObject;

public class MmsReceiver extends BroadcastReceiver {

    private static final String TAG = "MmsReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Telephony.Sms.Intents.WAP_PUSH_DELIVER_ACTION.equals(intent.getAction())) {
            return;
        }

        final PendingResult pendingResult = goAsync();
        final Context appContext = context.getApplicationContext();

        new Thread(() -> {
            try {
                MmsProviderStore.SaveResult saveResult = MmsProviderStore.saveIncomingMms(
                        appContext,
                        intent.getType(),
                        intent.getData(),
                        intent.getByteArrayExtra("data"),
                        intent.getExtras()
                );
                if (saveResult.duplicate) {
                    Log.i(TAG, "Skipping duplicate incoming MMS delivery");
                    pendingResult.setResultCode(Activity.RESULT_OK);
                    return;
                }

                JSONObject payload = buildPayload(intent, saveResult.message);
                DeviceEventWorker.enqueue(appContext, "app_log", payload);
                MmsDownloadManager.startDownload(appContext, saveResult.message, intent);
                DefaultSmsAppSupport.showIncomingMmsNotification(appContext, saveResult.message);
                pendingResult.setResultCode(Activity.RESULT_OK);
            } catch (Exception error) {
                Log.e(TAG, "Failed to handle incoming MMS", error);
                pendingResult.setResultCode(Activity.RESULT_CANCELED);
            } finally {
                pendingResult.finish();
            }
        }, "mms-receiver-worker").start();
    }

    private JSONObject buildPayload(Intent intent, MmsProviderStore.StoredMmsMessage message) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("category", "mms_received");
        payload.put("receivedAt", message == null ? System.currentTimeMillis() : message.receivedAtMs);
        payload.put("contentType", intent.getType());
        if (message != null) {
            payload.put("messageId", message.id);
            payload.put("pduSize", message.messageSize);
            payload.put("transactionId", message.transactionId);
            payload.put("threadId", message.threadId);
            payload.put("addresses", new JSONArray(message.addresses));
            payload.put("textParts", new JSONArray(message.textParts));
        }

        Uri data = intent.getData();
        if (data != null) {
            payload.put("uri", data.toString());
        }

        return payload;
    }
}
