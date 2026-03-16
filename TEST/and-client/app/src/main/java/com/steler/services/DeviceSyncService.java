package {{PACKAGE_NAME}}.services;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.util.Log;

import androidx.core.app.NotificationCompat;
import androidx.core.app.ServiceCompat;

import {{PACKAGE_NAME}}.MainActivity;
import {{PACKAGE_NAME}}.R;
import {{PACKAGE_NAME}}.sync.DeviceSyncClient;
import {{PACKAGE_NAME}}.sync.DeviceSyncManager;

public class DeviceSyncService extends Service {

    private static final String TAG = "DeviceSyncService";
    private static final String CHANNEL_ID = "device_sync_channel";
    private static final int NOTIFICATION_ID = 1001;
    private static final long HEARTBEAT_INTERVAL_MS = 60000L;

    private HandlerThread workerThread;
    private Handler workerHandler;
    private DeviceSyncClient syncClient;

    private final Runnable heartbeatTask = new Runnable() {
        @Override
        public void run() {
            performSync();
            if (workerHandler != null) {
                workerHandler.postDelayed(this, HEARTBEAT_INTERVAL_MS);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        DeviceSyncManager.schedulePeriodicSync(this);
        if (!startInForeground()) {
            return;
        }

        syncClient = new DeviceSyncClient(this);
        workerThread = new HandlerThread("device-sync-worker");
        workerThread.start();
        workerHandler = new Handler(workerThread.getLooper());
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (workerHandler == null) {
            stopSelf();
            return START_NOT_STICKY;
        }

        workerHandler.post(this::performSync);
        workerHandler.removeCallbacks(heartbeatTask);
        workerHandler.postDelayed(heartbeatTask, HEARTBEAT_INTERVAL_MS);
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (workerHandler != null) {
            workerHandler.removeCallbacksAndMessages(null);
        }

        if (workerThread != null) {
            workerThread.quitSafely();
        }

        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private boolean startInForeground() {
        Notification notification = buildNotification();
        int foregroundServiceType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
                ? ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                : 0;

        try {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, foregroundServiceType);
            return true;
        } catch (SecurityException error) {
            Log.w(TAG, "Foreground service rejected, switching to WorkManager fallback", error);
            DeviceSyncManager.enqueueImmediateSync(this, true);
            stopSelf();
            return false;
        } catch (RuntimeException error) {
            if (!DeviceSyncManager.isForegroundServiceStartFailure(error)) {
                throw error;
            }

            Log.w(TAG, "Foreground service unavailable, switching to WorkManager fallback", error);
            DeviceSyncManager.enqueueImmediateSync(this, true);
            stopSelf();
            return false;
        }
    }

    private void performSync() {
        if (syncClient == null) {
            return;
        }

        try {
            syncClient.performSync();
        } catch (Exception error) {
            Log.e(TAG, "Failed to sync device state", error);
        }
    }

    private Notification buildNotification() {
        createNotificationChannel();

        Intent launchIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                0,
                launchIntent,
                PendingIntent.FLAG_IMMUTABLE
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle(getString(R.string.sync_notification_title))
                .setContentText(getString(R.string.sync_notification_text))
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }

        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                getString(R.string.sync_channel_name),
                NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription(getString(R.string.sync_channel_description));

        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.createNotificationChannel(channel);
        }
    }
}
