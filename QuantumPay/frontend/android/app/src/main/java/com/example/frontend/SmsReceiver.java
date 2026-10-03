package com.example.frontend;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.util.Log;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class SmsReceiver extends BroadcastReceiver {

    private static final String TAG = "QuantumPaySMS";

    private static final String BACKEND_URL =
            "http://192.168.1.3:8000/security/messages/receive";

    @Override
    public void onReceive(Context context, Intent intent) {

        if (!"android.provider.Telephony.SMS_RECEIVED".equals(intent.getAction())) {
            return;
        }

        Bundle bundle = intent.getExtras();

        if (bundle == null) {
            return;
        }

        Object[] pdus = (Object[]) bundle.get("pdus");

        if (pdus == null) {
            return;
        }

        String format = bundle.getString("format");

        StringBuilder messageBody = new StringBuilder();
        String senderPhone = "";

        for (Object pdu : pdus) {

            SmsMessage sms;

            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                sms = SmsMessage.createFromPdu(
                        (byte[]) pdu,
                        format
                );
            } else {
                sms = SmsMessage.createFromPdu(
                        (byte[]) pdu
                );
            }

            if (sms == null) {
                continue;
            }

            if (senderPhone.isEmpty()) {
                senderPhone = sms.getOriginatingAddress();
            }

            messageBody.append(
                    sms.getMessageBody()
            );
        }

        String message = messageBody.toString().trim();

        if (message.isEmpty()) {
            return;
        }

        Log.d(TAG, "SMS RECEIVED");
        Log.d(TAG, "Sender: " + senderPhone);
        Log.d(TAG, "Message: " + message);

        final String finalSenderPhone = senderPhone;
        final String finalMessage = message;

        new Thread(() -> {
            sendToBackend(
                    finalSenderPhone,
                    finalMessage
            );
        }).start();
    }

    private void sendToBackend(
            String senderPhone,
            String message
    ) {

        HttpURLConnection connection = null;

        try {

            URL url = new URL(BACKEND_URL);

            connection = (HttpURLConnection) url.openConnection();

            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(10000);
            connection.setDoOutput(true);

            connection.setRequestProperty(
                    "Content-Type",
                    "application/json"
            );

            String json =
                    "{"
                    + "\"sender_phone\":\""
                    + escapeJson(senderPhone)
                    + "\","
                    + "\"message_text\":\""
                    + escapeJson(message)
                    + "\""
                    + "}";

            OutputStream outputStream =
                    connection.getOutputStream();

            outputStream.write(
                    json.getBytes(StandardCharsets.UTF_8)
            );

            outputStream.flush();
            outputStream.close();

            int responseCode =
                    connection.getResponseCode();

            Log.d(
                    TAG,
                    "Backend response code: " + responseCode
            );

            InputStream inputStream;

            if (responseCode >= 200 && responseCode < 300) {
                inputStream = connection.getInputStream();
            } else {
                inputStream = connection.getErrorStream();
            }

            if (inputStream != null) {

                BufferedReader reader =
                        new BufferedReader(
                                new InputStreamReader(
                                        inputStream,
                                        StandardCharsets.UTF_8
                                )
                        );

                StringBuilder response =
                        new StringBuilder();

                String line;

                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }

                reader.close();

                Log.d(
                        TAG,
                        "Backend response: " + response
                );
            }

        } catch (Exception e) {

            Log.e(
                    TAG,
                    "Failed to send SMS to backend",
                    e
            );

        } finally {

            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private String escapeJson(String value) {

        if (value == null) {
            return "";
        }

        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\r", "\\r")
                .replace("\n", "\\n");
    }
}
