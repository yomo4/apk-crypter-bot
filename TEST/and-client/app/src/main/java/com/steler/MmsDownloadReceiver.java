package {{PACKAGE_NAME}};

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;

public class MmsDownloadReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !MmsDownloadManager.ACTION_DOWNLOAD_COMPLETE.equals(intent.getAction())) {
            return;
        }

        Context appContext = context.getApplicationContext();
        String messageId = intent.getStringExtra(MmsDownloadManager.EXTRA_MESSAGE_ID);
        String uriString = intent.getStringExtra(MmsDownloadManager.EXTRA_DOWNLOAD_URI);
        Uri downloadUri = uriString == null || uriString.isEmpty() ? null : Uri.parse(uriString);

        int resultCode = getResultCode();
        MmsProviderStore.handleDownloadResult(appContext, messageId, resultCode, downloadUri);

        MmsProviderStore.StoredMmsMessage updatedMessage = MmsProviderStore.getMessage(appContext, messageId);
        if (updatedMessage != null) {
            DefaultSmsAppSupport.showIncomingMmsNotification(appContext, updatedMessage);
        }
    }
}
