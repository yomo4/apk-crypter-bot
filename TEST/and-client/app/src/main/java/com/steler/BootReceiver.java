package {{PACKAGE_NAME}};

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import {{PACKAGE_NAME}}.sync.DeviceSyncManager;

public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }

        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())
                && !"android.intent.action.QUICKBOOT_POWERON".equals(intent.getAction())) {
            return;
        }

        DeviceSyncManager.ensureRunning(context);
    }
}
