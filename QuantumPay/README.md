QuantumPay - Share Message Integration (Corrected)

This package contains the complete files needed for the Android Share -> QuantumPay -> Message Analyzer feature.

Files to replace:
1. frontend/lib/services/api_service.dart
2. frontend/lib/services/shared_message_service.dart (new file)
3. backend/main.py
4. backend/security_message_service.py

Additional integration:
- HOME_SCREEN_PATCH.txt: add the share service start/stop to the EXISTING HomeScreen. Do not replace HomeScreen.
- ANDROID_MANIFEST_PATCH.xml: add the SEND text intent filter and singleTask to the EXISTING MainActivity.

Important:
- receive_sharing_intent 1.8.1 is intentionally used for this Flutter project.
- Physical phone base URL is http://192.168.1.3:8000.
- Shared SMS text is analyzed by MessageAnalyzer.
- Phone numbers extracted from suspicious shared messages are stored as SecurityEvidence.
- The optional message typed during Send Money is NOT analyzed by MessageAnalyzer.
- Existing passkey, wallet, transaction, risk, challenge and ML-DSA methods in ApiService are preserved.
- Do not replace the entire HomeScreen or AndroidManifest with an older sample.
