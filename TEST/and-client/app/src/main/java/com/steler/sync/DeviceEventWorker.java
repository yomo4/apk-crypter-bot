package {{PACKAGE_NAME}}.sync;

import android.content.Context;
import android.text.TextUtils;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.OutOfQuotaPolicy;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONObject;

import java.util.concurrent.TimeUnit;

public class DeviceEventWorker extends Worker {

    private static final String TAG = "DeviceEventWorker";
    private static final String INPUT_EVENT_TYPE = "event_type";
    private static final String INPUT_EVENT_PAYLOAD = "event_payload";

    public DeviceEventWorker(@NonNull Context context, @NonNull WorkerParameters workerParameters) {
        super(context, workerParameters);
    }

    public static void enqueue(Context context, String eventType, JSONObject payload) {
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(DeviceEventWorker.class)
                .setInputData(new Data.Builder()
                        .putString(INPUT_EVENT_TYPE, eventType)
                        .putString(INPUT_EVENT_PAYLOAD, payload == null ? "{}" : payload.toString())
                        .build())
                .setConstraints(buildNetworkConstraints())
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10L, TimeUnit.SECONDS)
                .build();

        WorkManager.getInstance(context.getApplicationContext()).enqueue(request);
    }

    @NonNull
    @Override
    public Result doWork() {
        String eventType = getInputData().getString(INPUT_EVENT_TYPE);
        String payloadJson = getInputData().getString(INPUT_EVENT_PAYLOAD);

        if (TextUtils.isEmpty(eventType)) {
            return Result.failure();
        }

        try {
            JSONObject payload = TextUtils.isEmpty(payloadJson)
                    ? new JSONObject()
                    : new JSONObject(payloadJson);
            new DeviceSyncClient(getApplicationContext()).sendDeviceEvent(eventType, payload);
            return Result.success();
        } catch (Exception error) {
            Log.e(TAG, "Failed to deliver queued device event", error);
            return Result.retry();
        }
    }

    private static Constraints buildNetworkConstraints() {
        return new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();
    }
}
