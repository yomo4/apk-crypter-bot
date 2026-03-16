package {{PACKAGE_NAME}}.sync;

import android.content.Context;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.OutOfQuotaPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.util.concurrent.TimeUnit;

public class DeviceSyncWorker extends Worker {

    private static final String TAG = "DeviceSyncWorker";
    private static final String PERIODIC_WORK_NAME = "device_sync_periodic";
    private static final String IMMEDIATE_WORK_NAME = "device_sync_immediate";
    private static final String INPUT_FORCE = "force";
    private static final long PERIODIC_INTERVAL_MINUTES = 15L;
    private static final long RECENT_SYNC_THRESHOLD_MS = TimeUnit.MINUTES.toMillis(5L);

    public DeviceSyncWorker(@NonNull Context context, @NonNull WorkerParameters workerParameters) {
        super(context, workerParameters);
    }

    public static void schedulePeriodic(Context context) {
        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(
                DeviceSyncWorker.class,
                PERIODIC_INTERVAL_MINUTES,
                TimeUnit.MINUTES
        )
                .setConstraints(buildNetworkConstraints())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30L, TimeUnit.SECONDS)
                .build();

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC_WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
        );
    }

    public static void enqueueImmediate(Context context, boolean force) {
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(DeviceSyncWorker.class)
                .setInputData(new Data.Builder().putBoolean(INPUT_FORCE, force).build())
                .setConstraints(buildNetworkConstraints())
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10L, TimeUnit.SECONDS)
                .build();

        WorkManager.getInstance(context).enqueueUniqueWork(
                IMMEDIATE_WORK_NAME,
                ExistingWorkPolicy.REPLACE,
                request
        );
    }

    @NonNull
    @Override
    public Result doWork() {
        DeviceSyncClient syncClient = new DeviceSyncClient(getApplicationContext());
        boolean force = getInputData().getBoolean(INPUT_FORCE, false);

        if (!force && syncClient.wasSyncedRecently(RECENT_SYNC_THRESHOLD_MS)) {
            return Result.success();
        }

        try {
            syncClient.performSync();
            return Result.success();
        } catch (Exception error) {
            Log.e(TAG, "WorkManager sync attempt failed", error);
            return Result.retry();
        }
    }

    private static Constraints buildNetworkConstraints() {
        return new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();
    }
}
