import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../home/home_screen.dart';

class PaymentPinSetupScreen extends StatefulWidget {
  final int userId;
  final String userName;
  final String userEmail;
  final String loginPassword;

  const PaymentPinSetupScreen({
    super.key,
    required this.userId,
    required this.userName,
    required this.userEmail,
    required this.loginPassword,
  });

  @override
  State<PaymentPinSetupScreen> createState() => _PaymentPinSetupScreenState();
}

class _PaymentPinSetupScreenState extends State<PaymentPinSetupScreen> {
  final _formKey = GlobalKey<FormState>();

  final _pinController = TextEditingController();
  final _confirmController = TextEditingController();

  bool _obscurePin = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;

  @override
  void dispose() {
    _pinController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  String? _validatePin(String? value) {
    if (value == null || !RegExp(r'^\d{6}$').hasMatch(value)) {
      return 'Payment PIN must be exactly 6 digits';
    }
    return null;
  }

  String? _validateConfirm(String? value) {
    if (value == null || value != _pinController.text) {
      return 'PINs do not match';
    }
    return null;
  }

  String _cleanError(Object error) {
    var message = error.toString();
    if (message.startsWith('Exception: ')) {
      message = message.substring(11);
    }
    return message;
  }

  Future<void> _setupPin() async {
    if (!_formKey.currentState!.validate() || _isLoading) {
      return;
    }

    FocusManager.instance.primaryFocus?.unfocus();

    setState(() {
      _isLoading = true;
    });

    try {
      await ApiService.setupPaymentPin(
        userId: widget.userId,
        loginPassword: widget.loginPassword,
        paymentPin: _pinController.text,
      );

      if (!mounted) {
        return;
      }

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
    } catch (e) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_cleanError(e))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Payment PIN Setup'),
          automaticallyImplyLeading: false,
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 24),
                  Center(
                    child: Container(
                      width: 86,
                      height: 86,
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .primary
                            .withValues(alpha: 0.10),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.pin_outlined,
                        size: 48,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Create your Payment PIN',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Create a 6-digit PIN for viewing your balance and authorizing payments.',
                    style: TextStyle(
                      color: Colors.grey,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 28),
                  TextFormField(
                    controller: _pinController,
                    keyboardType: TextInputType.number,
                    obscureText: _obscurePin,
                    maxLength: 6,
                    validator: _validatePin,
                    decoration: InputDecoration(
                      labelText: 'Payment PIN',
                      hintText: 'Enter 6 digits',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscurePin = !_obscurePin;
                          });
                        },
                        icon: Icon(
                          _obscurePin
                              ? Icons.visibility_off
                              : Icons.visibility,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _confirmController,
                    keyboardType: TextInputType.number,
                    obscureText: _obscureConfirm,
                    maxLength: 6,
                    validator: _validateConfirm,
                    decoration: InputDecoration(
                      labelText: 'Confirm Payment PIN',
                      hintText: 'Re-enter 6 digits',
                      prefixIcon: const Icon(Icons.verified_user_outlined),
                      suffixIcon: IconButton(
                        onPressed: () {
                          setState(() {
                            _obscureConfirm = !_obscureConfirm;
                          });
                        },
                        icon: Icon(
                          _obscureConfirm
                              ? Icons.visibility_off
                              : Icons.visibility,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  SizedBox(
                    width: double.infinity,
                    height: 54,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _setupPin,
                      child: _isLoading
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                color: Colors.white,
                                strokeWidth: 2.5,
                              ),
                            )
                          : const Text(
                              'Create Payment PIN',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
