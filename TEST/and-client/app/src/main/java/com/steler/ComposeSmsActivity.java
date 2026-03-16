package {{PACKAGE_NAME}};

import android.app.Activity;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import java.util.List;

public class ComposeSmsActivity extends Activity {

    private static final String TAG = "ComposeSmsActivity";

    private EditText recipientsInput;
    private EditText messageInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_compose_sms);

        recipientsInput = findViewById(R.id.recipients_input);
        messageInput = findViewById(R.id.message_input);

        List<String> recipients = DefaultSmsAppSupport.extractRecipients(getIntent());
        recipientsInput.setText(TextUtils.join(", ", recipients));
        messageInput.setText(DefaultSmsAppSupport.extractMessageBody(getIntent()));

        Button sendButton = findViewById(R.id.send_button);
        Button cancelButton = findViewById(R.id.cancel_button);

        sendButton.setOnClickListener(view -> sendMessage());
        cancelButton.setOnClickListener(view -> finish());
    }

    private void sendMessage() {
        List<String> recipients = DefaultSmsAppSupport.parseRecipients(recipientsInput.getText().toString());
        String messageBody = messageInput.getText().toString().trim();

        if (recipients.isEmpty()) {
            Toast.makeText(this, R.string.compose_sms_missing_recipient, Toast.LENGTH_SHORT).show();
            return;
        }
        if (messageBody.isEmpty()) {
            Toast.makeText(this, R.string.compose_sms_missing_body, Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            DefaultSmsAppSupport.sendMessage(this, recipients, messageBody);
            Toast.makeText(this, R.string.compose_sms_sent, Toast.LENGTH_SHORT).show();
            finish();
        } catch (Exception error) {
            Log.e(TAG, "Failed to send SMS", error);
            Toast.makeText(this, R.string.compose_sms_send_failed, Toast.LENGTH_SHORT).show();
        }
    }
}
