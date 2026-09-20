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
  State<PaymentPinSetupScreen> createState() =>
      _PaymentPinSetupScreenState();
}

class _PaymentPinSetupScreenState extends State<PaymentPinSetupScreen> {
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _pinController = TextEditingController();
  final TextEditingController _confirmController = TextEditingController();

  bool _obscurePin = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;

  @override
  void dispose() {
    _pinController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  Future<void> _setupPin() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

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

      String message = e.toString();
      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  String? _validatePin(String? value) {
    if (value == null || !RegExp(r'^\d{6}$').hasMatch(value)) {
      return 'Enter exactly 6 digits';
    }
    return null;
  }

  String? _validateConfirm(String? value) {
    if (value != _pinController.text) {
      return 'PINs do not match';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
                const SizedBox(height: 30),
                const Center(
                  child: Icon(
                    Icons.pin_outlined,
                    size: 72,
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
                  'This 6-digit PIN is used for View Balance and Send Money.',
                  style: TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 30),
                TextFormField(
                  controller: _pinController,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  obscureText: _obscurePin,
                  validator: _validatePin,
                  decoration: InputDecoration(
                    labelText: '6-digit Payment PIN',
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
                const SizedBox(height: 10),
                TextFormField(
                  controller: _confirmController,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  obscureText: _obscureConfirm,
                  validator: _validateConfirm,
                  decoration: InputDecoration(
                    labelText: 'Confirm Payment PIN',
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
                const SizedBox(height: 30),
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _setupPin,
                    child: _isLoading
                        ? const CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2.5,
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
    );
  }
}
