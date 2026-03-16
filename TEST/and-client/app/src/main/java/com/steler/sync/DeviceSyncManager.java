package {{PACKAGE_NAME}}.sync;

import android.content.Context;
import android.content.Intent;
import android.util.Log;

import androidx.core.content.ContextCompat;

import {{PACKAGE_NAME}}.services.DeviceSyncService;

public final class DeviceSyncManager {

    private static final String TAG = "DeviceSyncManager";

    private DeviceSyncManager() {
    }

    public static void ensureRunning(Context context) {
        Context appContext = context.getApplicationContext();
        schedulePeriodicSync(appContext);

        try {
            ContextCompat.startForegroundService(appContext, new Intent(appContext, DeviceSyncService.class));
        } catch (SecurityException error) {
            Log.w(TAG, "Foreground service rejected, scheduling WorkManager fallback", error);
            enqueueImmediateSync(appContext, true);
        } catch (RuntimeException error) {
            if (!isForegroundServiceStartFailure(error)) {
                throw error;
            }

            Log.w(TAG, "Foreground service unavailable, scheduling WorkManager fallback", error);
            enqueueImmediateSync(appContext, true);
        }
    }

    public static void schedulePeriodicSync(Context context) {
        DeviceSyncWorker.schedulePeriodic(context.getApplicationContext());
    }

    public static void enqueueImmediateSync(Context context, boolean force) {
        DeviceSyncWorker.enqueueImmediate(context.getApplicationContext(), force);
    }

    public static boolean isForegroundServiceStartFailure(Throwable error) {
        return error instanceof IllegalStateException
                || error instanceof SecurityException;
    }
}
