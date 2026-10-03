import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/passkey_service.dart';
import '../home/home_screen.dart';
import 'payment_pin_setup_screen.dart';

class PasskeySetupScreen extends StatefulWidget {
  final int userId;
  final String userName;
  final String userEmail;
  final String loginPassword;
  final bool paymentPinSet;

  const PasskeySetupScreen({
    super.key,
    required this.userId,
    required this.userName,
    required this.userEmail,
    required this.loginPassword,
    required this.paymentPinSet,
  });

  @override
  State<PasskeySetupScreen> createState() => _PasskeySetupScreenState();
}

class _PasskeySetupScreenState extends State<PasskeySetupScreen> {
  final PasskeyService _passkeyService = PasskeyService();

  bool _isCreating = false;
  String? _errorMessage;

  Future<void> _createPasskey() async {
    if (_isCreating) {
      return;
    }

    FocusManager.instance.primaryFocus?.unfocus();

    setState(() {
      _isCreating = true;
      _errorMessage = null;
    });

    try {
      final supported = await _passkeyService.isSupported();

      if (!supported) {
        throw Exception(
          'Passkeys are not available on this device.',
        );
      }

      final optionsResult =
          await ApiService.getPasskeyRegistrationOptions(
        userId: widget.userId,
        password: widget.loginPassword,
      );

      final credential = await _passkeyService.registerPasskey(
        optionsJson: optionsResult['options'].toString(),
      );

      await ApiService.verifyPasskeyRegistration(
        stateId: optionsResult['state_id'] as int,
        credential: credential,
      );

      if (!mounted) {
        return;
      }

      if (!widget.paymentPinSet) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => PaymentPinSetupScreen(
              userId: widget.userId,
              userName: widget.userName,
              userEmail: widget.userEmail,
              loginPassword: widget.loginPassword,
            ),
          ),
        );
      } else {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => HomeScreen(
              userId: widget.userId,
              userName: widget.userName,
              userEmail: widget.userEmail,
            ),
          ),
        );
      }
    } catch (e) {
      if (!mounted) {
        return;
      }

      String message = e.toString();
      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      setState(() {
        _errorMessage = message;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isCreating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;

    return PopScope(
      canPop: false,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Secure Your Account'),
          automaticallyImplyLeading: false,
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 32),
            child: Column(
              children: [
                Container(
                  width: 92,
                  height: 92,
                  decoration: BoxDecoration(
                    color: primary.withValues(alpha: 0.10),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.fingerprint,
                    size: 54,
                    color: primary,
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Create your QuantumPay Passkey',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'A passkey is required for every QuantumPay account. '
                  'It is stored securely on your phone and protected by '
                  'your device PIN, fingerprint, or face unlock.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.grey,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 28),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: Colors.grey.withValues(alpha: 0.08),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.security_outlined),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'You cannot continue to the wallet until the passkey is created.',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            height: 1.35,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 18),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.error_outline,
                          color: Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(
                              color: Colors.red,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 30),
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton.icon(
                    onPressed: _isCreating ? null : _createPasskey,
                    icon: _isCreating
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2.4,
                            ),
                          )
                        : const Icon(Icons.key_outlined),
                    label: Text(
                      _isCreating
                          ? 'Creating Passkey...'
                          : 'Create Passkey',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Required step • No skip option',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
