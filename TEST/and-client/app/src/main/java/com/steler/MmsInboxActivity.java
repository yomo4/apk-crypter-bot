package {{PACKAGE_NAME}};

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

public class MmsInboxActivity extends Activity {

    private ListView listView;
    private TextView emptyView;
    private final List<MmsProviderStore.StoredMmsMessage> messages = new ArrayList<>();
    private boolean openedRequestedMessage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_mms_inbox);

        listView = findViewById(R.id.mms_list);
        emptyView = findViewById(R.id.empty_text);
        setTitle(R.string.mms_inbox_title);

        listView.setOnItemClickListener((parent, view, position, id) -> {
            MmsProviderStore.StoredMmsMessage selectedMessage = messages.get(position);
            MmsProviderStore.StoredMmsMessage fullMessage = MmsProviderStore.getMessage(this, selectedMessage.id);
            showMessageDetails(fullMessage == null ? selectedMessage : fullMessage);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        reloadMessages();
    }

    private void reloadMessages() {
        messages.clear();
        messages.addAll(MmsProviderStore.getMessages(this));

        List<String> labels = new ArrayList<>();
        for (MmsProviderStore.StoredMmsMessage message : messages) {
            labels.add(message.buildListLabel());
        }

        listView.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, labels));
        boolean hasMessages = !messages.isEmpty();
        listView.setEnabled(hasMessages);
        emptyView.setText(hasMessages ? "" : getString(R.string.mms_inbox_empty));

        maybeOpenRequestedMessage();
    }

    private void maybeOpenRequestedMessage() {
        if (openedRequestedMessage) {
            return;
        }

        String requestedMessageId = getIntent().getStringExtra(DefaultSmsAppSupport.EXTRA_MMS_RECORD_ID);
        if (requestedMessageId == null || requestedMessageId.isEmpty()) {
            return;
        }

        for (MmsProviderStore.StoredMmsMessage message : messages) {
            if (requestedMessageId.equals(message.id)) {
                openedRequestedMessage = true;
                MmsProviderStore.StoredMmsMessage fullMessage = MmsProviderStore.getMessage(this, message.id);
                showMessageDetails(fullMessage == null ? message : fullMessage);
                return;
            }
        }
    }

    private void showMessageDetails(MmsProviderStore.StoredMmsMessage message) {
        new AlertDialog.Builder(this)
                .setTitle(R.string.mms_inbox_detail_title)
                .setMessage(message.buildDetails())
                .setPositiveButton(android.R.string.ok, null)
                .show();
    }
}
