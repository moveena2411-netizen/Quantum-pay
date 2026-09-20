import 'package:flutter/material.dart';

import '../../services/api_service.dart';

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

  final TextEditingController _paymentPinController =
      TextEditingController();

  bool _obscurePaymentPin = true;
  bool _isSending = false;

  @override
  void dispose() {
    _receiverController.dispose();
    _amountController.dispose();
    _paymentPinController.dispose();
    super.dispose();
  }

  Future<void> _sendMoney() async {
    final receiver = _receiverController.text.trim();
    final amountText = _amountController.text.trim();
    final paymentPin = _paymentPinController.text.trim();

    if (receiver.isEmpty) {
      _showMessage('Please enter receiver email or phone');
      return;
    }

    if (receiver.toLowerCase() == widget.userEmail.toLowerCase()) {
      _showMessage('You cannot send money to yourself');
      return;
    }

    final amount = double.tryParse(amountText);

    if (amount == null || amount <= 0) {
      _showMessage('Please enter a valid amount');
      return;
    }

    if (!RegExp(r'^\d{6}$').hasMatch(paymentPin)) {
      _showMessage('Payment PIN must contain exactly 6 digits');
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      final result = await ApiService.sendMoney(
        senderId: widget.userId,
        receiver: receiver,
        amount: amount,
        paymentPin: paymentPin,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _isSending = false;
      });

      _showSuccessDialog(
        result['receiver']?.toString() ?? receiver,
        amount,
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

  void _showSuccessDialog(String receiver, double amount) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(
                Icons.check_circle,
                color: Colors.green,
              ),
              SizedBox(width: 10),
              Text('Payment Successful'),
            ],
          ),
          content: Text(
            '₹${amount.toStringAsFixed(2)} sent successfully to $receiver.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
                Navigator.of(context).pop(true);
              },
              child: const Text('Done'),
            ),
          ],
        );
      },
    );
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
      ),
    );
  }

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
              ),
            ),
            const SizedBox(height: 30),

            TextField(
              controller: _receiverController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Receiver Email / Phone',
                hintText: 'example@gmail.com',
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 18),

            TextField(
              controller: _amountController,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Amount',
                hintText: 'Enter amount',
                prefixIcon: Icon(Icons.currency_rupee),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 18),

            TextField(
              controller: _paymentPinController,
              obscureText: _obscurePaymentPin,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: InputDecoration(
                labelText: 'Payment PIN',
                hintText: 'Enter 6-digit Payment PIN',
                prefixIcon: const Icon(Icons.pin_outlined),
                counterText: '',
                suffixIcon: IconButton(
                  onPressed: () {
                    setState(() {
                      _obscurePaymentPin = !_obscurePaymentPin;
                    });
                  },
                  icon: Icon(
                    _obscurePaymentPin
                        ? Icons.visibility_off
                        : Icons.visibility,
                  ),
                ),
                border: const OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 8),

            const Text(
              'This is the same 6-digit PIN used to view your balance.',
              style: TextStyle(
                color: Colors.grey,
                fontSize: 12,
              ),
            ),

            const SizedBox(height: 30),

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
