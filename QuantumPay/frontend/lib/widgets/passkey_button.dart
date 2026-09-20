import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../services/passkey_service.dart';

class PasskeyButton extends StatefulWidget {
  final TextEditingController emailController;

  const PasskeyButton({
    super.key,
    required this.emailController,
  });

  @override
  State<PasskeyButton> createState() => _PasskeyButtonState();
}

class _PasskeyButtonState extends State<PasskeyButton> {
  final PasskeyService _passkeyService = PasskeyService();

  bool _isLoading = false;

  // --------------------------------------------------
  // CREATE PASSKEY
  // --------------------------------------------------

  Future<void> _createPasskey() async {
    if (_isLoading) {
      return;
    }

    final email = widget.emailController.text.trim();

    if (email.isEmpty) {
      _showMessage('Enter your email first');
      return;
    }

    // Dismiss the keyboard before opening the password dialog.
    FocusManager.instance.primaryFocus?.unfocus();

    final password = await _askForPassword();

    if (!mounted) {
      return;
    }

    if (password == null || password.isEmpty) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // ------------------------------------------------
      // CHECK DEVICE SUPPORT
      // ------------------------------------------------

      final supported = await _passkeyService.isSupported();

      if (!supported) {
        throw Exception(
          'Passkeys are not available on this device.',
        );
      }

      // ------------------------------------------------
      // VERIFY NORMAL LOGIN CREDENTIALS
      // ------------------------------------------------

      final loginResult = await ApiService.login(
        email,
        password,
      );

      final dynamic userIdValue = loginResult['user_id'];

      if (userIdValue == null) {
        throw Exception(
          'Unable to get QuantumPay user ID.',
        );
      }

      final int userId =
          userIdValue is int
              ? userIdValue
              : int.parse(userIdValue.toString());

      // ------------------------------------------------
      // GET WEBAUTHN REGISTRATION OPTIONS
      // ------------------------------------------------

      final optionsResult =
          await ApiService.getPasskeyRegistrationOptions(
        userId: userId,
        password: password,
      );

      final dynamic stateIdValue =
          optionsResult['state_id'];

      if (stateIdValue == null) {
        throw Exception(
          'Unable to start passkey registration.',
        );
      }

      final int stateId =
          stateIdValue is int
              ? stateIdValue
              : int.parse(stateIdValue.toString());

      final dynamic optionsValue =
          optionsResult['options'];

      if (optionsValue == null) {
        throw Exception(
          'Passkey registration options were not returned.',
        );
      }

      final String optionsJson =
          optionsValue.toString();

      if (optionsJson.isEmpty) {
        throw Exception(
          'Passkey registration options are empty.',
        );
      }

      // ------------------------------------------------
      // CREATE REAL ANDROID PASSKEY
      // ------------------------------------------------

      // Give Flutter one frame after the password dialog
      // closes before launching the native Credential Manager.
      await Future<void>.delayed(
        const Duration(milliseconds: 150),
      );

      if (!mounted) {
        return;
      }

      FocusManager.instance.primaryFocus?.unfocus();

      final credential =
          await _passkeyService.registerPasskey(
        optionsJson: optionsJson,
      );

      // ------------------------------------------------
      // SEND CREDENTIAL TO FASTAPI
      // ------------------------------------------------

      final verificationResult =
          await ApiService.verifyPasskeyRegistration(
        stateId: stateId,
        credential: credential,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _isLoading = false;
      });

      _showMessage(
        verificationResult['message']?.toString() ??
            'Passkey created successfully',
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isLoading = false;
      });

      String message = e.toString();

      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      _showMessage(message);
    }
  }

  // --------------------------------------------------
  // PASSWORD DIALOG
  // --------------------------------------------------

  Future<String?> _askForPassword() async {
    // The dialog owns its own controller.
    // This prevents it from being disposed while the
    // TextField is still being rebuilt or removed.
    final password = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return const _PasskeyPasswordDialog();
      },
    );

    // Let the dialog finish its widget teardown before
    // the native Credential Manager is launched.
    await Future<void>.delayed(
      const Duration(milliseconds: 100),
    );

    return password;
  }

  // --------------------------------------------------
  // MESSAGE
  // --------------------------------------------------

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // --------------------------------------------------
  // BUILD
  // --------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: OutlinedButton.icon(
        onPressed: _isLoading ? null : _createPasskey,
        icon: _isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                ),
              )
            : const Icon(
                Icons.fingerprint,
              ),
        label: Text(
          _isLoading
              ? 'Creating Passkey...'
              : 'Create Passkey',
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}

// ======================================================
// PASSWORD DIALOG WIDGET
// ======================================================

class _PasskeyPasswordDialog extends StatefulWidget {
  const _PasskeyPasswordDialog();

  @override
  State<_PasskeyPasswordDialog> createState() =>
      _PasskeyPasswordDialogState();
}

class _PasskeyPasswordDialogState
    extends State<_PasskeyPasswordDialog> {
  late final TextEditingController _controller;

  bool _obscure = true;

  @override
  void initState() {
    super.initState();

    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _continue() {
    FocusManager.instance.primaryFocus?.unfocus();

    Navigator.of(context).pop(
      _controller.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text(
        'Create Passkey',
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Enter your QuantumPay password '
            'to authorize passkey creation.',
          ),
          const SizedBox(height: 18),
          TextField(
            controller: _controller,
            autofocus: true,
            obscureText: _obscure,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              _continue();
            },
            decoration: InputDecoration(
              labelText: 'Password',
              prefixIcon: const Icon(
                Icons.lock_outline,
              ),
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() {
                    _obscure = !_obscure;
                  });
                },
                icon: Icon(
                  _obscure
                      ? Icons.visibility_off
                      : Icons.visibility,
                ),
              ),
              border: const OutlineInputBorder(),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () {
            FocusManager.instance.primaryFocus?.unfocus();

            Navigator.of(context).pop();
          },
          child: const Text(
            'Cancel',
          ),
        ),
        ElevatedButton(
          onPressed: _continue,
          child: const Text(
            'Continue',
          ),
        ),
      ],
    );
  }
}