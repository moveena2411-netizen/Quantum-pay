import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../history/history_screen.dart';
import '../payment/transaction_result_screen.dart';

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
  final TextEditingController _messageController =
      TextEditingController();

  bool _obscurePaymentPin = true;
  bool _isSending = false;

  @override
  void dispose() {
    _receiverController.dispose();
    _amountController.dispose();
    _paymentPinController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _sendMoney() async {
    final receiver = _receiverController.text.trim();
    final amountText = _amountController.text.trim();
    final paymentPin = _paymentPinController.text.trim();
    final message = _messageController.text.trim();

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

    FocusManager.instance.primaryFocus?.unfocus();

    setState(() {
      _isSending = true;
    });

    try {
      final result = await ApiService.sendMoney(
        senderId: widget.userId,
        receiver: receiver,
        amount: amount,
        paymentPin: paymentPin,
        message: message.isEmpty ? null : message,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _isSending = false;
      });

      final status = result['status']?.toString();

      // -----------------------------------------------------
      // HIGH INITIAL RISK -> SHOW CONTEXTUAL CHALLENGE
      // -----------------------------------------------------
      if (status == 'CHALLENGE_REQUIRED') {
        final pendingId = (result['pending_transaction_id'] as num?)?.toInt();

        if (pendingId == null) {
          _showMessage('Security challenge could not be started');
          return;
        }

        final rawQuestions = result['questions'];
        final questions = rawQuestions is List
            ? List<dynamic>.from(rawQuestions)
            : <dynamic>[];

        if (questions.isEmpty) {
          _showMessage('No security challenge questions were received');
          return;
        }

        await _showChallengeDialog(
          pendingTransactionId: pendingId,
          questions: questions,
          paymentPin: paymentPin,
        );
        return;
      }

      // -----------------------------------------------------
      // LOW OR FINAL MEDIUM -> TRANSACTION SUCCESS
      // -----------------------------------------------------
      if (status == 'SUCCESS') {
        await _showTransactionSuccessFromResult(
          result: result,
          fallbackReceiver: receiver,
          fallbackAmount: amount,
        );

        if (!mounted) {
          return;
        }

        _receiverController.clear();
        _amountController.clear();
        _paymentPinController.clear();
        _messageController.clear();
        return;
      }

      // -----------------------------------------------------
      // SAFETY FALLBACK
      // -----------------------------------------------------
      _showMessage(
        result['message']?.toString() ?? 'Transaction could not be completed',
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

  Future<void> _showTransactionSuccessFromResult({
    required Map<String, dynamic> result,
    required String fallbackReceiver,
    required double fallbackAmount,
  }) async {
    final timestampText = result['timestamp']?.toString();
    final parsedTimestamp = timestampText == null
        ? DateTime.now()
        : DateTime.tryParse(timestampText) ?? DateTime.now();

    final int? transactionId =
        (result['transaction_id'] as num?)?.toInt();
    final double? balanceAfter =
        (result['sender_balance'] as num?)?.toDouble();

    await _showTransactionSuccessSheet(
      sender: result['sender']?.toString() ?? widget.userEmail,
      receiver: result['receiver']?.toString() ?? fallbackReceiver,
      amount: (result['amount'] as num?)?.toDouble() ?? fallbackAmount,
      transactionDate: parsedTimestamp,
      transactionId: transactionId,
      balanceAfter: balanceAfter,
    );
  }

  Future<void> _showChallengeDialog({
    required int pendingTransactionId,
    required List<dynamic> questions,
    required String paymentPin,
  }) async {
    final Map<String, bool> answers = {};
    bool isSubmitting = false;

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Row(
                children: [
                  Icon(Icons.security_outlined),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text('Security Verification'),
                  ),
                ],
              ),
              content: SizedBox(
                width: double.maxFinite,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'This transaction requires additional security verification. Answer all questions honestly.',
                        style: TextStyle(fontSize: 13),
                      ),
                      const SizedBox(height: 18),
                      ...questions.map((item) {
                        if (item is! Map) {
                          return const SizedBox.shrink();
                        }

                        final id = item['id']?.toString();
                        final question = item['question']?.toString();

                        if (id == null || question == null) {
                          return const SizedBox.shrink();
                        }

                        final selected = answers[id];

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 18),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                question,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Row(
                                children: [
                                  Expanded(
                                    child: RadioListTile<bool>(
                                      contentPadding: EdgeInsets.zero,
                                      dense: true,
                                      title: const Text('Yes'),
                                      value: true,
                                      groupValue: selected,
                                      onChanged: isSubmitting
                                          ? null
                                          : (value) {
                                              setDialogState(() {
                                                answers[id] = value!;
                                              });
                                            },
                                    ),
                                  ),
                                  Expanded(
                                    child: RadioListTile<bool>(
                                      contentPadding: EdgeInsets.zero,
                                      dense: true,
                                      title: const Text('No'),
                                      value: false,
                                      groupValue: selected,
                                      onChanged: isSubmitting
                                          ? null
                                          : (value) {
                                              setDialogState(() {
                                                answers[id] = value!;
                                              });
                                            },
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isSubmitting
                      ? null
                      : () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final requiredIds = questions
                              .whereType<Map>()
                              .map((item) => item['id']?.toString())
                              .whereType<String>()
                              .toList();

                          final allAnswered = requiredIds.every(
                            answers.containsKey,
                          );

                          if (!allAnswered) {
                            ScaffoldMessenger.of(dialogContext).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Please answer all security questions',
                                ),
                              ),
                            );
                            return;
                          }

                          setDialogState(() {
                            isSubmitting = true;
                          });

                          try {
                            final result =
                                await ApiService.completeChallenge(
                              pendingTransactionId: pendingTransactionId,
                              answers: Map<String, bool>.from(answers),
                              paymentPin: paymentPin,
                            );

                            if (!mounted) {
                              return;
                            }

                            if (result['status'] == 'SUCCESS') {
                              Navigator.of(dialogContext).pop();
                              await _showTransactionSuccessFromResult(
                                result: result,
                                fallbackReceiver:
                                    _receiverController.text.trim(),
                                fallbackAmount:
                                    double.tryParse(
                                          _amountController.text.trim(),
                                        ) ??
                                        0,
                              );

                              if (!mounted) {
                                return;
                              }

                              _receiverController.clear();
                              _amountController.clear();
                              _paymentPinController.clear();
                              _messageController.clear();
                              return;
                            }

                            if (result['status'] == 'BLOCKED') {
                              Navigator.of(dialogContext).pop();
                              await _showBlockedDialog(result);
                              return;
                            }

                            setDialogState(() {
                              isSubmitting = false;
                            });

                            _showMessage(
                              result['message']?.toString() ??
                                  'Security verification failed',
                            );
                          } catch (e) {
                            if (!mounted) {
                              return;
                            }

                            setDialogState(() {
                              isSubmitting = false;
                            });

                            String message = e.toString();
                            if (message.startsWith('Exception: ')) {
                              message = message.substring(11);
                            }

                            _showMessage(message);
                          }
                        },
                  child: isSubmitting
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Verify & Continue'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _showBlockedDialog(Map<String, dynamic> result) async {
    final reasons = result['reasons'];
    final reasonText = reasons is List
        ? reasons.map((item) => '• ${item.toString()}').join('\n')
        : '';

    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.block_outlined),
              SizedBox(width: 10),
              Expanded(child: Text('Transaction Blocked')),
            ],
          ),
          content: SingleChildScrollView(
            child: Text(
              reasonText.isEmpty
                  ? (result['message']?.toString() ??
                      'Transaction blocked due to high security risk.')
                  : '${result['message'] ?? 'Transaction blocked due to high security risk.'}\n\n$reasonText',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showTransactionSuccessSheet({
    required String sender,
    required String receiver,
    required double amount,
    required DateTime transactionDate,
    required int? transactionId,
    required double? balanceAfter,
  }) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      isDismissible: false,
      enableDrag: true,
      builder: (sheetContext) {
        return TransactionResultScreen(
          userId: widget.userId,
          userEmail: widget.userEmail,
          sender: sender,
          receiver: receiver,
          amount: amount,
          transactionDate: transactionDate,
          transactionId: transactionId,
          balanceAfter: balanceAfter,
          onDone: () {
            Navigator.of(sheetContext).pop();
          },
          onViewHistory: () {
            Navigator.of(sheetContext).pop();
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => HistoryScreen(
                  userId: widget.userId,
                  userEmail: widget.userEmail,
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Send Money')),
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
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 30),
            TextField(
              controller: _receiverController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Receiver Email / Phone',
                hintText: 'example@gmail.com',
                prefixIcon: Icon(Icons.person_outline),
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
              controller: _messageController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Payment Message (Optional)',
                hintText: 'Enter payment message or request details',
                prefixIcon: Icon(Icons.message_outlined),
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
                          color: Colors.white,
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
