import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import 'transaction_result_screen.dart';

class SendMoneyScreen extends StatefulWidget {
  final int userId;
  final String userEmail;

  const SendMoneyScreen({
    super.key,
    required this.userId,
    required this.userEmail,
  });

  @override
  State<SendMoneyScreen> createState() => _SendMoneyScreenState();
}

class _SendMoneyScreenState extends State<SendMoneyScreen> {
  final TextEditingController _receiverController =
      TextEditingController();

  final TextEditingController _amountController =
      TextEditingController();

  final TextEditingController _passwordController =
      TextEditingController();

  bool _obscurePassword = true;
  bool _isSending = false;

  @override
  void dispose() {
    _receiverController.dispose();
    _amountController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // =========================================================
  // SEND MONEY
  // =========================================================

  Future<void> _sendMoney() async {
    final receiver = _receiverController.text.trim();
    final amountText = _amountController.text.trim();
    final password = _passwordController.text;

    // Validate receiver
    if (receiver.isEmpty) {
      _showMessage('Please enter receiver email or phone');
      return;
    }

    // Validate amount
    final amount = double.tryParse(amountText);

    if (amount == null || amount <= 0) {
      _showMessage('Please enter a valid amount');
      return;
    }

    // Prevent sending to yourself
    if (receiver.toLowerCase() == widget.userEmail.toLowerCase()) {
      _showMessage('You cannot send money to yourself');
      return;
    }

    // Validate password
    if (password.isEmpty) {
      _showMessage('Please enter your password');
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      // =======================================================
      // STEP 1: VERIFY PASSWORD
      // =======================================================

      await ApiService.login(
        widget.userEmail,
        password,
      );

      // =======================================================
      // STEP 2: SEND MONEY THROUGH BACKEND
      // =======================================================

      final result = await ApiService.sendMoney(
        senderId: widget.userId,
        receiver: receiver,
        amount: amount,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _isSending = false;
      });

      // =======================================================
      // STEP 3: OPEN TRANSACTION RESULT PAGE
      // =======================================================

      final String actualReceiver =
          result['receiver']?.toString() ?? receiver;

      final DateTime transactionDate = DateTime.now();

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => TransactionResultScreen(
            userId: widget.userId,
            receiver: actualReceiver,
            amount: amount,
            transactionDate: transactionDate,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isSending = false;
      });

      String message = e.toString();

      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      _showMessage(message);
    }
  }

  // =========================================================
  // ERROR / MESSAGE
  // =========================================================

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // =========================================================
  // UI
  // =========================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Send Money'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Send Money',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            const Text(
              'Transfer money securely to another QuantumPay user.',
              style: TextStyle(
                color: Colors.grey,
                fontSize: 15,
              ),
            ),

            const SizedBox(height: 30),

            // =================================================
            // RECEIVER
            // =================================================

            TextField(
              controller: _receiverController,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Receiver Email / Phone',
                hintText: 'example@gmail.com',
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 18),

            // =================================================
            // AMOUNT
            // =================================================

            TextField(
              controller: _amountController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Amount',
                hintText: 'Enter amount',
                prefixIcon: Icon(Icons.currency_rupee),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 18),

            // =================================================
            // PASSWORD
            // =================================================

            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) {
                if (!_isSending) {
                  _sendMoney();
                }
              },
              decoration: InputDecoration(
                labelText: 'Password',
                hintText: 'Enter your password',
                prefixIcon: const Icon(Icons.lock),
                suffixIcon: IconButton(
                  onPressed: () {
                    setState(() {
                      _obscurePassword = !_obscurePassword;
                    });
                  },
                  icon: Icon(
                    _obscurePassword
                        ? Icons.visibility
                        : Icons.visibility_off,
                  ),
                ),
                border: const OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 30),

            // =================================================
            // SEND BUTTON
            // =================================================

            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: _isSending ? null : _sendMoney,
                child: _isSending
                    ? const SizedBox(
                        height: 24,
                        width: 24,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'Send Money',
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
    );
  }
}