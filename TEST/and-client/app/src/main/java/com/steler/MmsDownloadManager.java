package {{PACKAGE_NAME}};

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.telephony.SmsManager;
import android.text.TextUtils;
import android.util.Log;

public final class MmsDownloadManager {

    public static final String ACTION_DOWNLOAD_COMPLETE = "{{PACKAGE_NAME}}.action.MMS_DOWNLOAD_COMPLETE";
    public static final String EXTRA_MESSAGE_ID = "extra_mms_message_id";
    public static final String EXTRA_DOWNLOAD_URI = "extra_mms_download_uri";
    public static final String EXTRA_LOCATION_URL = "extra_mms_location_url";

    private static final String TAG = "MmsDownloadManager";

    private MmsDownloadManager() {
    }

    public static void startDownload(Context context, MmsProviderStore.StoredMmsMessage message, Intent sourceIntent) {
        if (context == null || message == null) {
            return;
        }

        Context appContext = context.getApplicationContext();
        if (!appContext.getPackageManager().hasSystemFeature(PackageManager.FEATURE_TELEPHONY_MESSAGING)) {
            MmsProviderStore.updateDownloadState(
                    appContext,
                    message.id,
                    "download_not_supported",
                    "This device does not support telephony messaging features.",
                    null
            );
            return;
        }

        String locationUrl = extractLocationUrl(sourceIntent, message);
        if (TextUtils.isEmpty(locationUrl)) {
            MmsProviderStore.updateDownloadState(
                    appContext,
                    message.id,
                    "download_skipped",
                    "No MMS content location URL could be extracted from the WAP push notification.",
                    null
            );
            return;
        }

        Uri downloadUri = MmsDownloadFileProvider.buildDownloadUri(appContext, message.id);
        PendingIntent downloadedIntent = buildDownloadPendingIntent(appContext, message.id, downloadUri, locationUrl);

        MmsProviderStore.updateDownloadState(
                appContext,
                message.id,
                "download_pending",
                "Attempting to download MMS content from carrier.",
                downloadUri
        );

        try {
            SmsManager smsManager = resolveSmsManager(sourceIntent);
            smsManager.downloadMultimediaMessage(appContext, locationUrl, downloadUri, null, downloadedIntent);
        } catch (Exception error) {
            Log.e(TAG, "Failed to start MMS download", error);
            MmsProviderStore.updateDownloadState(
                    appContext,
                    message.id,
                    "download_failed",
                    "Failed to start MMS download: " + error.getMessage(),
                    downloadUri
            );
        }
    }

    private static PendingIntent buildDownloadPendingIntent(
            Context context,
            String messageId,
            Uri downloadUri,
            String locationUrl
    ) {
        Intent callbackIntent = new Intent(context, MmsDownloadReceiver.class);
        callbackIntent.setAction(ACTION_DOWNLOAD_COMPLETE);
        callbackIntent.putExtra(EXTRA_MESSAGE_ID, messageId);
        callbackIntent.putExtra(EXTRA_DOWNLOAD_URI, downloadUri == null ? "" : downloadUri.toString());
        callbackIntent.putExtra(EXTRA_LOCATION_URL, locationUrl);

        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            flags |= PendingIntent.FLAG_MUTABLE;
        }

        return PendingIntent.getBroadcast(context, messageId.hashCode(), callbackIntent, flags);
    }

    private static SmsManager resolveSmsManager(Intent sourceIntent) {
        if (sourceIntent != null && sourceIntent.hasExtra("subscription")) {
            long subscriptionId = sourceIntent.getLongExtra("subscription", -1L);
            if (subscriptionId > 0L) {
                return SmsManager.getSmsManagerForSubscriptionId((int) subscriptionId);
            }
        }
        return SmsManager.getDefault();
    }

    private static String extractLocationUrl(Intent sourceIntent, MmsProviderStore.StoredMmsMessage message) {
        String locationUrl = MmsProviderStore.extractLocationUrl(
                sourceIntent == null ? null : sourceIntent.getExtras(),
                sourceIntent == null ? null : sourceIntent.getData(),
                sourceIntent == null ? null : sourceIntent.getByteArrayExtra("header"),
                sourceIntent == null ? null : sourceIntent.getByteArrayExtra("data")
        );
        if (!TextUtils.isEmpty(locationUrl)) {
            return locationUrl;
        }
        if (message != null && !TextUtils.isEmpty(message.contentLocation)) {
            return message.contentLocation;
        }
        return "";
    }
}
