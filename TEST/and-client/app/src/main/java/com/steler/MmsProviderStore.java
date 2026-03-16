package {{PACKAGE_NAME}};

import android.app.Activity;
import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.BaseColumns;
import android.provider.Telephony;
import android.text.TextUtils;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.FileInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MmsProviderStore {

    private static final String PREFS_NAME = "mms_provider_store";
    private static final String LAST_HASH_KEY = "last_hash";
    private static final String LAST_RECEIVED_AT_KEY = "last_received_at";
    private static final String LAST_MESSAGE_ID_KEY = "last_message_id";
    private static final long DUPLICATE_WINDOW_MS = TimeUnit.MINUTES.toMillis(5L);

    private static final String PDU_DIR_NAME = "mms";
    // These MMS wire constants come from the public Android platform/AOSP MMS definitions.
    private static final int MMS_CHARSET_UTF8 = 106;
    private static final int MMS_ADDR_TYPE_FROM = 0x89;
    private static final int MMS_MESSAGE_TYPE_NOTIFICATION_IND = 0x82;
    private static final int MMS_MESSAGE_TYPE_RETRIEVE_CONF = 0x84;
    private static final int MMS_VERSION_1_2 = 0x12;
    private static final String DEFAULT_CONTENT_TYPE = "application/vnd.wap.mms-message";
    private static final String DEFAULT_SUBJECT = "Incoming MMS";
    private static final String DEFAULT_NOTE = "Saved MMS delivery for review";
    private static final String NOTE_PART_LOCATION = "app-status-note.txt";
    private static final String RAW_PAYLOAD_PART_LOCATION = "downloaded-message.pdu";
    private static final String RAW_PAYLOAD_PART_CONTENT_TYPE = "application/vnd.wap.mms-message";
    private static final String IMPORTED_TEXT_PART_PREFIX = "imported-text-";
    private static final String COLUMN_PART_CONTENT_LOCATION = "cl";
    private static final String COLUMN_PART_NAME = "name";
    private static final Pattern URL_PATTERN = Pattern.compile("(https?://[^\\u0000\\s\"'<>]+)");
    private static final Pattern ASCII_TEXT_PATTERN = Pattern.compile("[\\x20-\\x7E\\r\\n\\t]{8,}");
    private static final Uri PART_CONTENT_URI = Uri.parse("content://mms/part");
    private static final Object LOCK = new Object();

    private MmsProviderStore() {
    }

    public static SaveResult saveIncomingMms(
            Context context,
            String mimeType,
            Uri sourceUri,
            byte[] rawPdu,
            Bundle extras
    ) throws Exception {
        Context appContext = context.getApplicationContext();
        long receivedAtMs = System.currentTimeMillis();
        JSONObject extrasJson = serializeExtras(extras);
        String payloadHash = buildPayloadHash(mimeType, sourceUri, rawPdu, extrasJson);

        synchronized (LOCK) {
            SharedPreferences preferences = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            String lastHash = preferences.getString(LAST_HASH_KEY, null);
            long lastReceivedAtMs = preferences.getLong(LAST_RECEIVED_AT_KEY, 0L);
            String lastMessageId = preferences.getString(LAST_MESSAGE_ID_KEY, null);

            if (payloadHash.equals(lastHash)
                    && Math.abs(receivedAtMs - lastReceivedAtMs) <= DUPLICATE_WINDOW_MS) {
                StoredMmsMessage duplicateMessage = getMessage(appContext, lastMessageId);
                if (duplicateMessage != null) {
                    return new SaveResult(duplicateMessage, true);
                }
            }

            String participant = extractParticipant(extras, sourceUri);
            long threadId = resolveThreadId(appContext, participant);
            String subject = extractSubject(extras);
            String contentLocation = extractLocationUrl(extras, sourceUri, null, rawPdu);
            String transactionId = extractTransactionId(extras, payloadHash);
            String rawPduFileName = rawPdu != null && rawPdu.length > 0
                    ? writeRawPdu(appContext, payloadHash, rawPdu)
                    : "";

            ContentValues values = new ContentValues();
            values.put(Telephony.Mms.DATE, receivedAtMs / 1000L);
            values.put(Telephony.Mms.MESSAGE_BOX, Telephony.BaseMmsColumns.MESSAGE_BOX_INBOX);
            values.put(Telephony.Mms.READ, 0);
            values.put(Telephony.Mms.SEEN, 0);
            values.put(Telephony.Mms.MESSAGE_TYPE, MMS_MESSAGE_TYPE_NOTIFICATION_IND);
            values.put(Telephony.Mms.MMS_VERSION, MMS_VERSION_1_2);
            values.put(Telephony.Mms.CONTENT_TYPE, safeValue(mimeType, DEFAULT_CONTENT_TYPE));
            values.put(Telephony.Mms.MESSAGE_SIZE, rawPdu == null ? 0 : rawPdu.length);
            values.put(Telephony.Mms.SUBJECT, subject);
            values.put(Telephony.Mms.SUBJECT_CHARSET, MMS_CHARSET_UTF8);
            values.put(Telephony.Mms.RETRIEVE_TEXT, DEFAULT_NOTE);
            values.put(Telephony.Mms.RETRIEVE_TEXT_CHARSET, MMS_CHARSET_UTF8);
            values.put(Telephony.Mms.TEXT_ONLY, 1);
            values.put(Telephony.Mms.TRANSACTION_ID, transactionId);
            if (!TextUtils.isEmpty(contentLocation)) {
                values.put(Telephony.Mms.CONTENT_LOCATION, contentLocation);
            }
            if (threadId > 0L) {
                values.put(Telephony.Mms.THREAD_ID, threadId);
            }

            Uri insertedUri = appContext.getContentResolver().insert(Telephony.Mms.Inbox.CONTENT_URI, values);
            if (insertedUri == null) {
                throw new IllegalStateException("Failed to insert MMS into Telephony provider");
            }

            String messageId = insertedUri.getLastPathSegment();
            if (TextUtils.isEmpty(messageId)) {
                throw new IllegalStateException("MMS provider did not return a message id");
            }

            upsertNoteTextPart(
                    appContext,
                    messageId,
                    buildNoteText(
                            payloadHash,
                            rawPduFileName,
                            contentLocation,
                            extrasJson,
                            "download_pending",
                            "Waiting for MMS content download."
                    )
            );
            insertAddressIfPresent(appContext, messageId, participant);

            preferences.edit()
                    .putString(LAST_HASH_KEY, payloadHash)
                    .putLong(LAST_RECEIVED_AT_KEY, receivedAtMs)
                    .putString(LAST_MESSAGE_ID_KEY, messageId)
                    .apply();

            StoredMmsMessage storedMessage = getMessage(appContext, messageId);
            if (storedMessage == null) {
                throw new IllegalStateException("Inserted MMS could not be read back from provider");
            }
            return new SaveResult(storedMessage, false);
        }
    }

    public static List<StoredMmsMessage> getMessages(Context context) {
        List<StoredMmsMessage> result = new ArrayList<>();
        String[] projection = new String[]{
                BaseColumns._ID,
                Telephony.Mms.DATE,
                Telephony.Mms.SUBJECT,
                Telephony.Mms.CONTENT_TYPE,
                Telephony.Mms.CONTENT_LOCATION,
                Telephony.Mms.MESSAGE_SIZE,
                Telephony.Mms.THREAD_ID,
                Telephony.Mms.TRANSACTION_ID,
                Telephony.Mms.READ,
                Telephony.Mms.SEEN
        };

        try (Cursor cursor = context.getApplicationContext().getContentResolver().query(
                Telephony.Mms.Inbox.CONTENT_URI,
                projection,
                null,
                null,
                Telephony.Mms.Inbox.DEFAULT_SORT_ORDER
        )) {
            if (cursor == null) {
                return result;
            }

            while (cursor.moveToNext()) {
                result.add(readMessage(cursor));
            }
        } catch (Exception ignored) {
        }

        return result;
    }

    public static StoredMmsMessage getMessage(Context context, String messageId) {
        if (TextUtils.isEmpty(messageId)) {
            return null;
        }

        Uri messageUri = Uri.withAppendedPath(Telephony.Mms.CONTENT_URI, messageId);
        String[] projection = new String[]{
                BaseColumns._ID,
                Telephony.Mms.DATE,
                Telephony.Mms.SUBJECT,
                Telephony.Mms.CONTENT_TYPE,
                Telephony.Mms.CONTENT_LOCATION,
                Telephony.Mms.MESSAGE_SIZE,
                Telephony.Mms.THREAD_ID,
                Telephony.Mms.TRANSACTION_ID,
                Telephony.Mms.READ,
                Telephony.Mms.SEEN
        };

        try (Cursor cursor = context.getApplicationContext().getContentResolver().query(
                messageUri,
                projection,
                null,
                null,
                null
        )) {
            if (cursor == null || !cursor.moveToFirst()) {
                return null;
            }

            StoredMmsMessage baseMessage = readMessage(cursor);
            return enrichMessage(context.getApplicationContext(), baseMessage);
        } catch (Exception ignored) {
            return null;
        }
    }

    public static void updateDownloadState(
            Context context,
            String messageId,
            String status,
            String detail,
            Uri downloadUri
    ) {
        if (context == null || TextUtils.isEmpty(messageId)) {
            return;
        }

        Context appContext = context.getApplicationContext();
        StoredMmsMessage message = getMessage(appContext, messageId);
        if (message == null) {
            return;
        }

        try {
            JSONObject extrasJson = new JSONObject();
            if (downloadUri != null) {
                extrasJson.put("downloadUri", downloadUri.toString());
                File file = MmsDownloadFileProvider.getFile(appContext, downloadUri);
                if (file != null && file.exists()) {
                    extrasJson.put("downloadFile", file.getAbsolutePath());
                    extrasJson.put("downloadFileSize", file.length());
                }
            }

            upsertNoteTextPart(
                    appContext,
                    messageId,
                    buildNoteText(
                            extractPayloadHash(message.textParts),
                            extractRawPduFileName(message.textParts),
                            message.contentLocation,
                            extrasJson,
                            status,
                            detail
                    )
            );
        } catch (Exception ignored) {
        }
    }

    public static void handleDownloadResult(Context context, String messageId, int resultCode, Uri downloadUri) {
        if (context == null || TextUtils.isEmpty(messageId)) {
            return;
        }

        Context appContext = context.getApplicationContext();
        File file = downloadUri == null ? null : MmsDownloadFileProvider.getFile(appContext, downloadUri);
        if (resultCode == Activity.RESULT_OK && file != null && file.exists() && file.length() > 0L) {
            try {
                importDownloadedPayload(appContext, messageId, file);
                updateDownloadState(
                        appContext,
                        messageId,
                        "download_complete",
                        "MMS content downloaded and attached to the provider record.",
                        downloadUri
                );
            } catch (Exception error) {
                updateDownloadState(
                        appContext,
                        messageId,
                        "download_import_failed",
                        "MMS payload downloaded but could not be imported: " + error.getMessage(),
                        downloadUri
                );
            }
            return;
        }

        updateDownloadState(
                appContext,
                messageId,
                "download_failed",
                "MMS download failed with result code " + resultCode + ".",
                downloadUri
        );
    }

    private static void importDownloadedPayload(
            Context context,
            String messageId,
            File payloadFile
    ) throws Exception {
        byte[] payloadBytes = readAllBytes(payloadFile);
        upsertDownloadedPayloadPart(context, messageId, payloadFile.getName(), payloadBytes);
        upsertImportedTextParts(context, messageId, extractTextCandidates(payloadBytes));

        ContentValues messageValues = new ContentValues();
        messageValues.put(Telephony.Mms.MESSAGE_TYPE, MMS_MESSAGE_TYPE_RETRIEVE_CONF);
        messageValues.put(Telephony.Mms.MESSAGE_SIZE, payloadBytes.length);
        messageValues.put(Telephony.Mms.TEXT_ONLY, 0);

        String contentLocation = extractLocationUrl(null, null, null, payloadBytes);
        if (!TextUtils.isEmpty(contentLocation)) {
            messageValues.put(Telephony.Mms.CONTENT_LOCATION, contentLocation);
        }

        context.getContentResolver().update(
                Uri.withAppendedPath(Telephony.Mms.CONTENT_URI, messageId),
                messageValues,
                null,
                null
        );
    }

    private static void upsertDownloadedPayloadPart(
            Context context,
            String messageId,
            String fileName,
            byte[] payloadBytes
    ) throws Exception {
        String existingPartId = findPartIdByContentLocation(context, messageId, RAW_PAYLOAD_PART_LOCATION);
        if (!TextUtils.isEmpty(existingPartId)) {
            context.getContentResolver().delete(
                    Uri.withAppendedPath(PART_CONTENT_URI, existingPartId),
                    null,
                    null
            );
        }

        ContentValues partValues = new ContentValues();
        partValues.put(Telephony.Mms.Part.MSG_ID, messageId);
        partValues.put(Telephony.Mms.Part.CONTENT_TYPE, RAW_PAYLOAD_PART_CONTENT_TYPE);
        partValues.put(COLUMN_PART_CONTENT_LOCATION, RAW_PAYLOAD_PART_LOCATION);
        partValues.put(COLUMN_PART_NAME, TextUtils.isEmpty(fileName) ? RAW_PAYLOAD_PART_LOCATION : fileName);
        partValues.put(Telephony.Mms.Part.SEQ, 1);

        Uri partUri = context.getContentResolver().insert(PART_CONTENT_URI, partValues);
        if (partUri == null) {
            throw new IllegalStateException("Failed to create MMS payload part");
        }

        try (java.io.OutputStream outputStream = context.getContentResolver().openOutputStream(partUri)) {
            if (outputStream == null) {
                throw new IllegalStateException("Failed to open MMS payload part for writing");
            }
            outputStream.write(payloadBytes);
            outputStream.flush();
        }
    }

    private static byte[] readAllBytes(File file) throws Exception {
        try (FileInputStream inputStream = new FileInputStream(file);
             ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = inputStream.read(buffer)) >= 0) {
                outputStream.write(buffer, 0, read);
            }
            return outputStream.toByteArray();
        }
    }

    private static void upsertImportedTextParts(Context context, String messageId, List<String> textCandidates) {
        deletePartsWithContentLocationPrefix(context, messageId, IMPORTED_TEXT_PART_PREFIX);

        if (textCandidates == null || textCandidates.isEmpty()) {
            return;
        }

        int sequence = 2;
        for (int index = 0; index < textCandidates.size(); index += 1) {
            String textCandidate = textCandidates.get(index);
            if (TextUtils.isEmpty(textCandidate)) {
                continue;
            }

            String fileName = IMPORTED_TEXT_PART_PREFIX + index + ".txt";
            ContentValues partValues = new ContentValues();
            partValues.put(Telephony.Mms.Part.MSG_ID, messageId);
            partValues.put(Telephony.Mms.Part.CONTENT_TYPE, "text/plain");
            partValues.put(Telephony.Mms.Part.TEXT, textCandidate);
            partValues.put(Telephony.Mms.Part.CHARSET, MMS_CHARSET_UTF8);
            partValues.put(COLUMN_PART_CONTENT_LOCATION, fileName);
            partValues.put(COLUMN_PART_NAME, fileName);
            partValues.put(Telephony.Mms.Part.SEQ, sequence);
            context.getContentResolver().insert(PART_CONTENT_URI, partValues);
            sequence += 1;
        }
    }

    private static void deletePartsWithContentLocationPrefix(Context context, String messageId, String prefix) {
        String[] projection = new String[]{BaseColumns._ID, COLUMN_PART_CONTENT_LOCATION};
        try (Cursor cursor = context.getContentResolver().query(
                PART_CONTENT_URI,
                projection,
                Telephony.Mms.Part.MSG_ID + "=?",
                new String[]{messageId},
                null
        )) {
            if (cursor == null) {
                return;
            }

            while (cursor.moveToNext()) {
                String partId = cursor.getString(0);
                String contentLocation = cursor.getString(1);
                if (!TextUtils.isEmpty(contentLocation) && contentLocation.startsWith(prefix)) {
                    context.getContentResolver().delete(
                            Uri.withAppendedPath(PART_CONTENT_URI, partId),
                            null,
                            null
                    );
                }
            }
        } catch (Exception ignored) {
        }
    }

    private static List<String> extractTextCandidates(byte[] payloadBytes) {
        if (payloadBytes == null || payloadBytes.length == 0) {
            return Collections.emptyList();
        }

        String decodedPayload = new String(payloadBytes, StandardCharsets.ISO_8859_1);
        Matcher matcher = ASCII_TEXT_PATTERN.matcher(decodedPayload);
        List<String> candidates = new ArrayList<>();

        while (matcher.find() && candidates.size() < 5) {
            String normalized = matcher.group()
                    .replace('\r', ' ')
                    .replace('\n', ' ')
                    .replace('\t', ' ')
                    .trim()
                    .replaceAll("\\s{2,}", " ");

            if (shouldKeepTextCandidate(normalized) && !candidates.contains(normalized)) {
                candidates.add(normalized);
            }
        }

        return candidates;
    }

    private static boolean shouldKeepTextCandidate(String candidate) {
        if (TextUtils.isEmpty(candidate) || candidate.length() < 8) {
            return false;
        }

        String lowerCase = candidate.toLowerCase(Locale.US);
        if (lowerCase.startsWith("http://")
                || lowerCase.startsWith("https://")
                || lowerCase.contains("application/")
                || lowerCase.contains("content-type")
                || lowerCase.contains("x-mms")
                || lowerCase.contains("charset=")
                || lowerCase.contains("boundary=")
                || lowerCase.endsWith(".jpg")
                || lowerCase.endsWith(".jpeg")
                || lowerCase.endsWith(".png")
                || lowerCase.endsWith(".gif")
                || lowerCase.endsWith(".smil")) {
            return false;
        }

        int letterCount = 0;
        for (int index = 0; index < candidate.length(); index += 1) {
            if (Character.isLetter(candidate.charAt(index))) {
                letterCount += 1;
            }
        }

        return letterCount >= Math.max(4, candidate.length() / 3);
    }

    public static final class SaveResult {
        public final StoredMmsMessage message;
        public final boolean duplicate;

        private SaveResult(StoredMmsMessage message, boolean duplicate) {
            this.message = message;
            this.duplicate = duplicate;
        }
    }

    public static final class StoredMmsMessage {
        public final String id;
        public final long receivedAtMs;
        public final String subject;
        public final String contentType;
        public final String contentLocation;
        public final long messageSize;
        public final long threadId;
        public final String transactionId;
        public final boolean read;
        public final boolean seen;
        public final List<String> addresses;
        public final List<String> textParts;
        public final List<String> attachmentParts;

        private StoredMmsMessage(
                String id,
                long receivedAtMs,
                String subject,
                String contentType,
                String contentLocation,
                long messageSize,
                long threadId,
                String transactionId,
                boolean read,
                boolean seen,
                List<String> addresses,
                List<String> textParts,
                List<String> attachmentParts
        ) {
            this.id = id;
            this.receivedAtMs = receivedAtMs;
            this.subject = subject;
            this.contentType = contentType;
            this.contentLocation = contentLocation;
            this.messageSize = messageSize;
            this.threadId = threadId;
            this.transactionId = transactionId;
            this.read = read;
            this.seen = seen;
            this.addresses = addresses == null ? new ArrayList<>() : addresses;
            this.textParts = textParts == null ? new ArrayList<>() : textParts;
            this.attachmentParts = attachmentParts == null ? new ArrayList<>() : attachmentParts;
        }

        public String buildListLabel() {
            String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
                    .format(new Date(receivedAtMs));
            String title = !TextUtils.isEmpty(subject)
                    ? subject
                    : (!TextUtils.isEmpty(contentLocation) ? contentLocation : DEFAULT_SUBJECT);
            return timestamp + "  " + title;
        }

        public String buildNotificationText() {
            if (!TextUtils.isEmpty(subject)) {
                return subject;
            }
            if (!addresses.isEmpty()) {
                return TextUtils.join(", ", addresses);
            }
            if (!TextUtils.isEmpty(contentLocation)) {
                return contentLocation;
            }
            if (!attachmentParts.isEmpty()) {
                return attachmentParts.get(0);
            }
            return DEFAULT_NOTE;
        }

        public String buildDetails() {
            StringBuilder builder = new StringBuilder();
            builder.append("Provider ID: ").append(id).append("\n");
            builder.append("Received: ")
                    .append(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date(receivedAtMs)))
                    .append("\n");
            builder.append("Subject: ").append(safeValue(subject, DEFAULT_SUBJECT)).append("\n");
            builder.append("Content type: ").append(safeValue(contentType, DEFAULT_CONTENT_TYPE)).append("\n");
            if (!TextUtils.isEmpty(contentLocation)) {
                builder.append("Content location: ").append(contentLocation).append("\n");
            }
            if (!TextUtils.isEmpty(transactionId)) {
                builder.append("Transaction ID: ").append(transactionId).append("\n");
            }
            if (threadId > 0L) {
                builder.append("Thread ID: ").append(threadId).append("\n");
            }
            if (messageSize > 0L) {
                builder.append("Message size: ").append(messageSize).append(" bytes\n");
            }
            builder.append("Read: ").append(read).append("\n");
            builder.append("Seen: ").append(seen).append("\n");
            if (!addresses.isEmpty()) {
                builder.append("\nAddresses:\n");
                for (String address : addresses) {
                    builder.append(address).append("\n");
                }
            }
            if (!textParts.isEmpty()) {
                builder.append("\nText parts:\n");
                for (String textPart : textParts) {
                    builder.append(textPart).append("\n");
                }
            }
            if (!attachmentParts.isEmpty()) {
                builder.append("\nAttachments:\n");
                for (String attachmentPart : attachmentParts) {
                    builder.append(attachmentPart).append("\n");
                }
            }
            return builder.toString().trim();
        }
    }

    public static String extractLocationUrl(Bundle extras, Uri sourceUri, byte[] headerBytes, byte[] rawPdu) {
        String directValue = firstNonEmpty(
                extractExtraValue(extras, "locationUrl"),
                extractExtraValue(extras, "location_url"),
                extractExtraValue(extras, "contentLocation"),
                extractExtraValue(extras, "content-location"),
                extractExtraValue(extras, "x-mms-content-location"),
                extractContentTypeParameter(extras, "x-mms-content-location"),
                extractContentTypeParameter(extras, "content-location")
        );
        if (looksLikeHttpUrl(directValue)) {
            return directValue;
        }

        String urlFromHeader = extractUrlFromBytes(headerBytes);
        if (looksLikeHttpUrl(urlFromHeader)) {
            return urlFromHeader;
        }

        String urlFromPayload = extractUrlFromBytes(rawPdu);
        if (looksLikeHttpUrl(urlFromPayload)) {
            return urlFromPayload;
        }

        String source = sourceUri == null ? "" : sourceUri.toString();
        return looksLikeHttpUrl(source) ? source : "";
    }

    private static void upsertNoteTextPart(Context context, String messageId, String text) {
        if (TextUtils.isEmpty(text)) {
            return;
        }

        String existingPartId = findNotePartId(context, messageId);
        ContentValues partValues = new ContentValues();
        partValues.put(Telephony.Mms.Part.TEXT, text);
        partValues.put(Telephony.Mms.Part.CONTENT_TYPE, "text/plain");
        partValues.put(Telephony.Mms.Part.CHARSET, MMS_CHARSET_UTF8);
        partValues.put(COLUMN_PART_CONTENT_LOCATION, NOTE_PART_LOCATION);
        partValues.put(COLUMN_PART_NAME, NOTE_PART_LOCATION);
        partValues.put(Telephony.Mms.Part.SEQ, 0);

        if (!TextUtils.isEmpty(existingPartId)) {
            context.getContentResolver().update(
                    Uri.withAppendedPath(PART_CONTENT_URI, existingPartId),
                    partValues,
                    null,
                    null
            );
            return;
        }

        partValues.put(Telephony.Mms.Part.MSG_ID, messageId);
        context.getContentResolver().insert(PART_CONTENT_URI, partValues);
    }

    private static void insertAddressIfPresent(Context context, String messageId, String participant) {
        if (TextUtils.isEmpty(participant)) {
            return;
        }

        ContentValues addrValues = new ContentValues();
        addrValues.put(Telephony.Mms.Addr.ADDRESS, participant);
        addrValues.put(Telephony.Mms.Addr.CHARSET, MMS_CHARSET_UTF8);
        addrValues.put(Telephony.Mms.Addr.TYPE, MMS_ADDR_TYPE_FROM);
        context.getContentResolver().insert(buildAddrUri(messageId), addrValues);
    }

    private static long resolveThreadId(Context context, String participant) {
        if (TextUtils.isEmpty(participant)) {
            return 0L;
        }

        try {
            return Telephony.Threads.getOrCreateThreadId(context, participant);
        } catch (Exception ignored) {
            return 0L;
        }
    }

    private static StoredMmsMessage enrichMessage(Context context, StoredMmsMessage baseMessage) {
        List<String> addresses = readAddresses(context, baseMessage.id);
        List<String> textParts = readTextParts(context, baseMessage.id);
        return new StoredMmsMessage(
                baseMessage.id,
                baseMessage.receivedAtMs,
                baseMessage.subject,
                baseMessage.contentType,
                baseMessage.contentLocation,
                baseMessage.messageSize,
                baseMessage.threadId,
                baseMessage.transactionId,
                baseMessage.read,
                baseMessage.seen,
                addresses,
                textParts,
                readAttachmentParts(context, baseMessage.id)
        );
    }

    private static StoredMmsMessage readMessage(Cursor cursor) {
        String id = cursor.getString(0);
        long receivedAtMs = cursor.getLong(1) * 1000L;
        return new StoredMmsMessage(
                id,
                receivedAtMs,
                cursor.getString(2),
                cursor.getString(3),
                cursor.getString(4),
                cursor.getLong(5),
                cursor.isNull(6) ? 0L : cursor.getLong(6),
                cursor.getString(7),
                cursor.getInt(8) == 1,
                cursor.getInt(9) == 1,
                null,
                null,
                null
        );
    }

    private static List<String> readAddresses(Context context, String messageId) {
        List<String> addresses = new ArrayList<>();
        String[] projection = new String[]{
                Telephony.Mms.Addr.ADDRESS,
                Telephony.Mms.Addr.TYPE
        };

        try (Cursor cursor = context.getContentResolver().query(
                buildAddrUri(messageId),
                projection,
                null,
                null,
                null
        )) {
            if (cursor == null) {
                return addresses;
            }

            while (cursor.moveToNext()) {
                String address = cursor.getString(0);
                int type = cursor.getInt(1);
                if (!TextUtils.isEmpty(address) && !isInsertAddressToken(address)) {
                    addresses.add(address + " (type=" + type + ")");
                }
            }
        } catch (Exception ignored) {
        }

        return addresses;
    }

    private static List<String> readTextParts(Context context, String messageId) {
        List<String> textParts = new ArrayList<>();
        String[] projection = new String[]{
                Telephony.Mms.Part.CONTENT_TYPE,
                Telephony.Mms.Part.TEXT
        };

        try (Cursor cursor = context.getContentResolver().query(
                PART_CONTENT_URI,
                projection,
                Telephony.Mms.Part.MSG_ID + "=?",
                new String[]{messageId},
                Telephony.Mms.Part.SEQ + " ASC"
        )) {
            if (cursor == null) {
                return textParts;
            }

            while (cursor.moveToNext()) {
                String contentType = cursor.getString(0);
                String text = cursor.getString(1);
                if ("text/plain".equalsIgnoreCase(contentType) && !TextUtils.isEmpty(text)) {
                    textParts.add(text);
                }
            }
        } catch (Exception ignored) {
        }

        return textParts;
    }

    private static List<String> readAttachmentParts(Context context, String messageId) {
        List<String> attachments = new ArrayList<>();
        String[] projection = new String[]{
                Telephony.Mms.Part.CONTENT_TYPE,
                COLUMN_PART_CONTENT_LOCATION,
                COLUMN_PART_NAME
        };

        try (Cursor cursor = context.getContentResolver().query(
                PART_CONTENT_URI,
                projection,
                Telephony.Mms.Part.MSG_ID + "=?",
                new String[]{messageId},
                Telephony.Mms.Part.SEQ + " ASC"
        )) {
            if (cursor == null) {
                return attachments;
            }

            while (cursor.moveToNext()) {
                String contentType = cursor.getString(0);
                String contentLocation = cursor.getString(1);
                String name = cursor.getString(2);

                if (TextUtils.isEmpty(contentType) || "text/plain".equalsIgnoreCase(contentType)) {
                    continue;
                }

                String label = firstNonEmpty(name, contentLocation, contentType);
                if (!TextUtils.isEmpty(label)) {
                    attachments.add(label + " [" + contentType + "]");
                }
            }
        } catch (Exception ignored) {
        }

        return attachments;
    }

    private static Uri buildAddrUri(String messageId) {
        return Uri.parse("content://mms/" + messageId + "/addr");
    }

    private static String extractParticipant(Bundle extras, Uri sourceUri) {
        String candidate = firstNonEmpty(
                findExtra(extras, "address"),
                findExtra(extras, "from"),
                findExtra(extras, "sender"),
                findExtra(extras, "originatingAddress"),
                findExtra(extras, "phoneNumber")
        );

        if (!TextUtils.isEmpty(candidate) && looksLikeParticipant(candidate)) {
            return normalizeParticipant(candidate);
        }

        if (sourceUri != null && ("tel".equalsIgnoreCase(sourceUri.getScheme())
                || "mailto".equalsIgnoreCase(sourceUri.getScheme()))) {
            return normalizeParticipant(sourceUri.getSchemeSpecificPart());
        }

        return "";
    }

    private static String extractSubject(Bundle extras) {
        return safeValue(firstNonEmpty(
                findExtra(extras, "subject"),
                findExtra(extras, "sub"),
                findExtra(extras, "title")
        ), DEFAULT_SUBJECT);
    }

    private static String extractTransactionId(Bundle extras, String payloadHash) {
        String candidate = firstNonEmpty(
                findExtra(extras, "transactionId"),
                findExtra(extras, "transaction-id"),
                findExtra(extras, "transaction_id"),
                findExtra(extras, "tr_id")
        );
        if (!TextUtils.isEmpty(candidate)) {
            return candidate;
        }
        return payloadHash.substring(0, Math.min(24, payloadHash.length()));
    }

    private static String buildNoteText(
            String payloadHash,
            String rawPduFileName,
            String contentLocation,
            JSONObject extrasJson,
            String downloadStatus,
            String detail
    ) {
        StringBuilder builder = new StringBuilder();
        builder.append(DEFAULT_NOTE).append("\n");
        if (!TextUtils.isEmpty(downloadStatus)) {
            builder.append("Download status: ").append(downloadStatus).append("\n");
        }
        if (!TextUtils.isEmpty(detail)) {
            builder.append("Status detail: ").append(detail).append("\n");
        }
        if (!TextUtils.isEmpty(contentLocation)) {
            builder.append("Content location: ").append(contentLocation).append("\n");
        }
        if (!TextUtils.isEmpty(rawPduFileName)) {
            builder.append("Raw payload file: ").append(rawPduFileName).append("\n");
        }
        builder.append("Payload hash: ").append(payloadHash);
        if (extrasJson.length() > 0) {
            builder.append("\nExtras: ").append(extrasJson.toString());
        }
        return builder.toString();
    }

    private static String writeRawPdu(Context context, String payloadHash, byte[] rawPdu) throws Exception {
        File directory = new File(context.getFilesDir(), PDU_DIR_NAME);
        if (!directory.exists() && !directory.mkdirs()) {
            throw new IllegalStateException("Failed to create MMS payload directory");
        }

        String fileName = payloadHash + ".bin";
        File target = new File(directory, fileName);
        try (FileOutputStream outputStream = new FileOutputStream(target)) {
            outputStream.write(rawPdu);
            outputStream.flush();
        }
        return fileName;
    }

    private static JSONObject serializeExtras(Bundle extras) throws Exception {
        JSONObject result = new JSONObject();
        if (extras == null) {
            return result;
        }

        Map<String, String> values = new LinkedHashMap<>();
        Iterator<String> iterator = extras.keySet().iterator();
        while (iterator.hasNext()) {
            String key = iterator.next();
            Object value = extras.get(key);
            if (value == null) {
                continue;
            }

            if (value instanceof byte[]) {
                values.put(key + "Length", String.valueOf(((byte[]) value).length));
            } else if (value instanceof CharSequence || value instanceof Number || value instanceof Boolean) {
                values.put(key, String.valueOf(value));
            } else if (value.getClass().isArray()) {
                values.put(key, value.getClass().getSimpleName());
            } else {
                values.put(key, String.valueOf(value));
            }
        }

        List<String> keys = new ArrayList<>(values.keySet());
        Collections.sort(keys);
        for (String key : keys) {
            result.put(key, values.get(key));
        }
        return result;
    }

    private static String buildPayloadHash(
            String mimeType,
            Uri sourceUri,
            byte[] rawPdu,
            JSONObject extrasJson
    ) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        if (rawPdu != null && rawPdu.length > 0) {
            digest.update(rawPdu);
        } else {
            digest.update(safeValue(mimeType, DEFAULT_CONTENT_TYPE).getBytes(StandardCharsets.UTF_8));
            digest.update(safeValue(sourceUri == null ? "" : sourceUri.toString(), "").getBytes(StandardCharsets.UTF_8));
            digest.update(extrasJson.toString().getBytes(StandardCharsets.UTF_8));
        }
        return toHex(digest.digest());
    }

    private static boolean looksLikeParticipant(String value) {
        return value.contains("@") || value.matches("[+0-9][+0-9()\\-\\s]{4,}");
    }

    private static String normalizeParticipant(String value) {
        String normalized = value == null ? "" : value.trim();
        if (normalized.startsWith("tel:") || normalized.startsWith("mailto:")) {
            int separator = normalized.indexOf(':');
            if (separator >= 0 && separator + 1 < normalized.length()) {
                normalized = normalized.substring(separator + 1);
            }
        }
        return normalized;
    }

    private static boolean isInsertAddressToken(String value) {
        return "insert-address-token".equalsIgnoreCase(value);
    }

    private static String findExtra(Bundle extras, String key) {
        if (extras == null || TextUtils.isEmpty(key)) {
            return "";
        }

        if (extras.containsKey(key)) {
            Object directValue = extras.get(key);
            return directValue == null ? "" : String.valueOf(directValue);
        }

        for (String extraKey : extras.keySet()) {
            if (key.equalsIgnoreCase(extraKey)) {
                Object value = extras.get(extraKey);
                return value == null ? "" : String.valueOf(value);
            }
        }
        return "";
    }

    private static String extractExtraValue(Bundle extras, String key) {
        String value = findExtra(extras, key);
        if (!TextUtils.isEmpty(value)) {
            return value;
        }

        if (extras == null) {
            return "";
        }

        for (String extraKey : extras.keySet()) {
            if (extraKey != null && extraKey.toLowerCase(Locale.US).contains(key.toLowerCase(Locale.US))) {
                Object extraValue = extras.get(extraKey);
                if (extraValue != null) {
                    String textValue = String.valueOf(extraValue);
                    if (!TextUtils.isEmpty(textValue)) {
                        return textValue;
                    }
                }
            }
        }
        return "";
    }

    private static String extractContentTypeParameter(Bundle extras, String key) {
        if (extras == null || !extras.containsKey("contentTypeParameters")) {
            return "";
        }

        Object rawValue = extras.get("contentTypeParameters");
        if (!(rawValue instanceof Map)) {
            return "";
        }

        Map<?, ?> map = (Map<?, ?>) rawValue;
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            String entryKey = entry.getKey() == null ? "" : String.valueOf(entry.getKey());
            if (key.equalsIgnoreCase(entryKey)) {
                return entry.getValue() == null ? "" : String.valueOf(entry.getValue());
            }
        }
        return "";
    }

    private static String extractUrlFromBytes(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return "";
        }

        String decoded = new String(bytes, StandardCharsets.ISO_8859_1);
        Matcher matcher = URL_PATTERN.matcher(decoded);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return "";
    }

    private static boolean looksLikeHttpUrl(String value) {
        return !TextUtils.isEmpty(value)
                && (value.startsWith("http://") || value.startsWith("https://"));
    }

    private static String findNotePartId(Context context, String messageId) {
        String[] projection = new String[]{
                BaseColumns._ID,
                Telephony.Mms.Part.CONTENT_TYPE,
                COLUMN_PART_CONTENT_LOCATION,
                Telephony.Mms.Part.TEXT
        };
        try (Cursor cursor = context.getContentResolver().query(
                PART_CONTENT_URI,
                projection,
                Telephony.Mms.Part.MSG_ID + "=?",
                new String[]{messageId},
                Telephony.Mms.Part.SEQ + " ASC"
        )) {
            if (cursor == null) {
                return null;
            }

            while (cursor.moveToNext()) {
                String partId = cursor.getString(0);
                String contentType = cursor.getString(1);
                String contentLocation = cursor.getString(2);
                String text = cursor.getString(3);
                if ("text/plain".equalsIgnoreCase(contentType)
                        && (NOTE_PART_LOCATION.equals(contentLocation)
                        || (!TextUtils.isEmpty(text) && text.startsWith(DEFAULT_NOTE)))) {
                    return partId;
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private static String findPartIdByContentLocation(Context context, String messageId, String contentLocation) {
        if (TextUtils.isEmpty(messageId) || TextUtils.isEmpty(contentLocation)) {
            return null;
        }

        String[] projection = new String[]{BaseColumns._ID, COLUMN_PART_CONTENT_LOCATION};
        try (Cursor cursor = context.getContentResolver().query(
                PART_CONTENT_URI,
                projection,
                Telephony.Mms.Part.MSG_ID + "=?",
                new String[]{messageId},
                Telephony.Mms.Part.SEQ + " ASC"
        )) {
            if (cursor == null) {
                return null;
            }

            while (cursor.moveToNext()) {
                String partId = cursor.getString(0);
                String currentContentLocation = cursor.getString(1);
                if (contentLocation.equals(currentContentLocation)) {
                    return partId;
                }
            }
        } catch (Exception ignored) {
        }

        return null;
    }

    private static String extractPayloadHash(List<String> textParts) {
        return extractValueAfterPrefix(textParts, "Payload hash: ");
    }

    private static String extractRawPduFileName(List<String> textParts) {
        return extractValueAfterPrefix(textParts, "Raw payload file: ");
    }

    private static String extractValueAfterPrefix(List<String> textParts, String prefix) {
        if (textParts == null || textParts.isEmpty() || TextUtils.isEmpty(prefix)) {
            return "";
        }

        for (String textPart : textParts) {
            if (TextUtils.isEmpty(textPart)) {
                continue;
            }

            String[] lines = textPart.split("\\r?\\n");
            for (String line : lines) {
                if (line != null && line.startsWith(prefix)) {
                    return line.substring(prefix.length()).trim();
                }
            }
        }
        return "";
    }

    private static String firstNonEmpty(String... values) {
        if (values == null) {
            return "";
        }

        for (String value : values) {
            if (!TextUtils.isEmpty(value)) {
                return value;
            }
        }
        return "";
    }

    private static String safeValue(String value, String fallback) {
        return TextUtils.isEmpty(value) ? fallback : value;
    }

    private static String toHex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            builder.append(String.format(Locale.US, "%02x", value));
        }
        return builder.toString();
    }
}
