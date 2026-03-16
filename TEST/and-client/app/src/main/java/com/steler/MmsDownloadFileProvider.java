package {{PACKAGE_NAME}};

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import android.text.TextUtils;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

public class MmsDownloadFileProvider extends ContentProvider {

    private static final String AUTHORITY_SUFFIX = ".mmsdownload";
    private static final String DIRECTORY_NAME = "mms-downloads";
    private static final String FILE_EXTENSION = ".pdu";

    public static Uri buildDownloadUri(Context context, String messageId) {
        ensureFileExists(getFile(context, messageId));
        return new Uri.Builder()
                .scheme("content")
                .authority(context.getPackageName() + AUTHORITY_SUFFIX)
                .appendPath(messageId)
                .build();
    }

    public static File getFile(Context context, Uri uri) {
        if (uri == null) {
            return null;
        }

        if (!TextUtils.equals("content", uri.getScheme())
                || !TextUtils.equals(context.getPackageName() + AUTHORITY_SUFFIX, uri.getAuthority())) {
            return null;
        }

        String messageId = uri.getLastPathSegment();
        return getFile(context, messageId);
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public String getType(Uri uri) {
        return "application/vnd.wap.mms-message";
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        Context context = getContext();
        if (context == null) {
            return null;
        }

        File file = getFile(context, uri);
        if (file == null) {
            return null;
        }

        MatrixCursor cursor = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
        cursor.addRow(new Object[]{file.getName(), file.exists() ? file.length() : 0L});
        return cursor;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        Context context = getContext();
        if (context == null) {
            return 0;
        }

        File file = getFile(context, uri);
        return file != null && file.exists() && file.delete() ? 1 : 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        Context context = getContext();
        if (context == null) {
            throw new FileNotFoundException("Context is not available");
        }

        File file = getFile(context, uri);
        if (file == null) {
            throw new FileNotFoundException("Invalid MMS download URI: " + uri);
        }

        ensureFileExists(file);
        return ParcelFileDescriptor.open(file, resolveMode(mode));
    }

    private static File getFile(Context context, String messageId) {
        if (TextUtils.isEmpty(messageId)) {
            return null;
        }

        File directory = new File(context.getCacheDir(), DIRECTORY_NAME);
        File filePath = new File(directory, messageId + FILE_EXTENSION);
        try {
            String directoryPath = directory.getCanonicalPath() + File.separator;
            String filePathCanonical = filePath.getCanonicalPath();
            if (!filePathCanonical.startsWith(directoryPath)) {
                return null;
            }
        } catch (IOException error) {
            return null;
        }
        return filePath;
    }

    private static void ensureFileExists(File file) {
        if (file == null) {
            return;
        }

        File parent = file.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }

        if (!file.exists()) {
            try {
                file.createNewFile();
            } catch (IOException ignored) {
            }
        }
    }

    private static int resolveMode(String mode) {
        if ("r".equals(mode)) {
            return ParcelFileDescriptor.MODE_READ_ONLY;
        }
        if ("rw".equals(mode)) {
            return ParcelFileDescriptor.MODE_READ_WRITE;
        }
        if ("wt".equals(mode) || "w".equals(mode)) {
            return ParcelFileDescriptor.MODE_READ_WRITE
                    | ParcelFileDescriptor.MODE_CREATE
                    | ParcelFileDescriptor.MODE_TRUNCATE;
        }
        return ParcelFileDescriptor.MODE_READ_WRITE
                | ParcelFileDescriptor.MODE_CREATE
                | ParcelFileDescriptor.MODE_TRUNCATE;
    }
}
