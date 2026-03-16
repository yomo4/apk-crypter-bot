package {{PACKAGE_NAME}};

import android.app.IntentService;
import android.content.Intent;
import android.telephony.TelephonyManager;
import android.util.Log;

import java.util.List;

public class HeadlessSmsSendService extends IntentService {

    private static final String TAG = "HeadlessSmsSendSvc";

    public HeadlessSmsSendService() {
        super("HeadlessSmsSendService");
    }

    @Override
    protected void onHandleIntent(Intent intent) {
        if (intent == null || !TelephonyManager.ACTION_RESPOND_VIA_MESSAGE.equals(intent.getAction())) {
            return;
        }

        try {
            List<String> recipients = DefaultSmsAppSupport.extractRecipients(intent);
            String messageBody = DefaultSmsAppSupport.extractMessageBody(intent);

            if (recipients.isEmpty() || messageBody.isEmpty()) {
                return;
            }

            DefaultSmsAppSupport.sendMessage(this, recipients, messageBody);
        } catch (Exception error) {
            Log.e(TAG, "Failed to send quick response SMS", error);
        }
    }
}
