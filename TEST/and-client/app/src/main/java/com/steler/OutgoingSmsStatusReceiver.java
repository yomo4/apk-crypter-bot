package {{PACKAGE_NAME}};

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class OutgoingSmsStatusReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) {
            return;
        }

        String action = intent.getAction();
        if (OutgoingSmsTracker.ACTION_SMS_SENT.equals(action)) {
            OutgoingSmsTracker.handleSentResult(context.getApplicationContext(), intent, getResultCode());
            return;
        }

        if (OutgoingSmsTracker.ACTION_SMS_DELIVERED.equals(action)) {
            OutgoingSmsTracker.handleDeliveredResult(context.getApplicationContext(), intent, getResultCode());
        }
    }
}
