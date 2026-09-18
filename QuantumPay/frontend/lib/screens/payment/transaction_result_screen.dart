import 'package:flutter/material.dart';

import '../history/history_screen.dart';

class TransactionResultScreen extends StatefulWidget {
  final int userId;
  final String receiver;
  final double amount;
  final DateTime transactionDate;

  const TransactionResultScreen({
    super.key,
    required this.userId,
    required this.receiver,
    required this.amount,
    required this.transactionDate,
  });

  @override
  State<TransactionResultScreen> createState() =>
      _TransactionResultScreenState();
}

class _TransactionResultScreenState
    extends State<TransactionResultScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;

  late Animation<double> _tickAnimation;
  late Animation<Offset> _sheetAnimation;

  bool _showDetails = false;

  @override
  void initState() {
    super.initState();

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );

    _tickAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.elasticOut,
    );

    _sheetAnimation = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(
          0.35,
          1.0,
          curve: Curves.easeOutCubic,
        ),
      ),
    );

    _animationController.forward();

    // Show the payment details after the success tick appears.
    Future.delayed(
      const Duration(milliseconds: 650),
      () {
        if (mounted) {
          setState(() {
            _showDetails = true;
          });
        }
      },
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  // =========================================================
  // DATE & TIME
  // =========================================================

  String _formatDate(DateTime date) {
    final day = date.day.toString().padLeft(2, '0');
    final month = date.month.toString().padLeft(2, '0');
    final year = date.year.toString();

    final hour = date.hour % 12 == 0 ? 12 : date.hour % 12;
    final minute = date.minute.toString().padLeft(2, '0');

    final period = date.hour >= 12 ? 'PM' : 'AM';

    return '$day/$month/$year • $hour:$minute $period';
  }

  // =========================================================
  // OPEN HISTORY
  // =========================================================

  void _openHistory() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (context) => HistoryScreen(
          userId: widget.userId,
        ),
      ),
    );
  }

  // =========================================================
  // DONE
  // =========================================================

  void _done() {
    Navigator.pop(context, true);
  }

  // =========================================================
  // UI
  // =========================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Stack(
          children: [
            // =================================================
            // SUCCESS AREA
            // =================================================

            Center(
              child: AnimatedBuilder(
                animation: _tickAnimation,
                builder: (context, child) {
                  return Transform.scale(
                    scale: _tickAnimation.value,
                    child: child,
                  );
                },
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 78,
                      height: 78,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(0xFFE8F5E9),
                      ),
                      child: const Icon(
                        Icons.check,
                        color: Colors.green,
                        size: 48,
                      ),
                    ),

                    const SizedBox(height: 18),

                    const Text(
                      'Payment Successful',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // =================================================
            // PAYMENT DETAILS SLIDE-UP
            // =================================================

            if (_showDetails)
              Positioned.fill(
                child: Align(
                  alignment: Alignment.bottomCenter,
                  child: SlideTransition(
                    position: _sheetAnimation,
                    child: _buildPaymentDetails(),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // =========================================================
  // PAYMENT DETAILS CARD
  // =========================================================

  Widget _buildPaymentDetails() {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(
        maxHeight: 520,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(28),
        ),
        boxShadow: [
          BoxShadow(
            blurRadius: 20,
            spreadRadius: 2,
            offset: Offset(0, -5),
            color: Colors.black12,
          ),
        ],
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(
          24,
          12,
          24,
          24,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // =================================================
            // DRAG HANDLE
            // =================================================

            Center(
              child: Container(
                width: 45,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),

            const SizedBox(height: 22),

            // =================================================
            // SUCCESS HEADER
            // =================================================

            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Color(0xFFE8F5E9),
                  ),
                  child: const Icon(
                    Icons.check,
                    color: Colors.green,
                    size: 30,
                  ),
                ),

                const SizedBox(width: 14),

                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Payment Successful',
                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Money sent successfully',
                        style: TextStyle(
                          color: Colors.grey,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 25),

            // =================================================
            // AMOUNT
            // =================================================

            Center(
              child: Text(
                '₹${widget.amount.toStringAsFixed(2)}',
                style: const TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),

            const SizedBox(height: 26),

            const Divider(),

            const SizedBox(height: 8),

            // =================================================
            // PAYMENT DETAILS
            // =================================================

            const Text(
              'Payment Details',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 16),

            _detailRow(
              icon: Icons.person_outline,
              title: 'Receiver',
              value: widget.receiver,
            ),

            const SizedBox(height: 16),

            _detailRow(
              icon: Icons.currency_rupee,
              title: 'Amount',
              value: '₹${widget.amount.toStringAsFixed(2)}',
            ),

            const SizedBox(height: 16),

            _detailRow(
              icon: Icons.calendar_today_outlined,
              title: 'Date & Time',
              value: _formatDate(widget.transactionDate),
            ),

            const SizedBox(height: 16),

            _detailRow(
              icon: Icons.check_circle_outline,
              title: 'Status',
              value: 'Successful',
              valueColor: Colors.green,
            ),

            const SizedBox(height: 25),

            // =================================================
            // VIEW HISTORY
            // =================================================

            SizedBox(
              width: double.infinity,
              height: 50,
              child: OutlinedButton.icon(
                onPressed: _openHistory,
                icon: const Icon(Icons.history),
                label: const Text(
                  'View Transaction History',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 12),

            // =================================================
            // DONE
            // =================================================

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _done,
                child: const Text(
                  'Done',
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

  // =========================================================
  // DETAIL ROW
  // =========================================================

  Widget _detailRow({
    required IconData icon,
    required String title,
    required String value,
    Color? valueColor,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 22,
          color: Colors.grey.shade700,
        ),

        const SizedBox(width: 14),

        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.grey,
                  fontSize: 13,
                ),
              ),

              const SizedBox(height: 4),

              Text(
                value,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: valueColor,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}