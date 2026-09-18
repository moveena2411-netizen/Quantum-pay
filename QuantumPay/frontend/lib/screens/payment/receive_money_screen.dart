import 'package:flutter/material.dart';

import '../../services/api_service.dart';

class ReceiveMoneyScreen extends StatefulWidget {
  final int userId;

  const ReceiveMoneyScreen({
    super.key,
    required this.userId,
  });

  @override
  State<ReceiveMoneyScreen> createState() =>
      _ReceiveMoneyScreenState();
}

class _ReceiveMoneyScreenState
    extends State<ReceiveMoneyScreen> {
  final TextEditingController _amountController =
      TextEditingController();

  bool _isReceiving = false;

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  // =========================================================
  // RECEIVE MONEY
  // =========================================================

  Future<void> _receiveMoney() async {
    final amountText = _amountController.text.trim();
    final amount = double.tryParse(amountText);

    if (amount == null || amount <= 0) {
      _showMessage('Please enter a valid amount');
      return;
    }

    setState(() {
      _isReceiving = true;
    });

    try {
      final result = await ApiService.receiveMoney(
        userId: widget.userId,
        amount: amount,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _isReceiving = false;
      });

      _showSuccessDialog(
        amount,
        result['balance'],
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isReceiving = false;
      });

      String message = e.toString();

      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      _showMessage(message);
    }
  }

  // =========================================================
  // SUCCESS
  // =========================================================

  void _showSuccessDialog(
    double amount,
    dynamic newBalance,
  ) {
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
              Text('Money Received'),
            ],
          ),
          content: Text(
            '₹${amount.toStringAsFixed(2)} has been added to your wallet.',
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

  // =========================================================
  // MESSAGE
  // =========================================================

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
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
        title: const Text('Receive Money'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Receive Money',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            const Text(
              'Add money to your QuantumPay wallet.',
              style: TextStyle(
                color: Colors.grey,
              ),
            ),

            const SizedBox(height: 30),

            TextField(
              controller: _amountController,
              keyboardType:
                  const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Amount',
                hintText: 'Enter amount',
                prefixIcon: Icon(Icons.currency_rupee),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 30),

            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed:
                    _isReceiving ? null : _receiveMoney,
                child: _isReceiving
                    ? const SizedBox(
                        height: 24,
                        width: 24,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'Receive Money',
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