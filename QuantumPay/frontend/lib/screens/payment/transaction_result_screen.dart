import 'package:flutter/material.dart';

class TransactionResultScreen extends StatelessWidget {
  final int userId;
  final String userEmail;
  final String sender;
  final String receiver;
  final double amount;
  final DateTime transactionDate;
  final int? transactionId;
  final double? balanceAfter;
  final VoidCallback onDone;
  final VoidCallback onViewHistory;

  const TransactionResultScreen({
    super.key,
    required this.userId,
    required this.userEmail,
    required this.sender,
    required this.receiver,
    required this.amount,
    required this.transactionDate,
    required this.onDone,
    required this.onViewHistory,
    this.transactionId,
    this.balanceAfter,
  });

  String _formatDate(DateTime value) {
    final local = value.toLocal();
    final hour = local.hour % 12 == 0 ? 12 : local.hour % 12;
    final minute = local.minute.toString().padLeft(2, '0');
    final second = local.second.toString().padLeft(2, '0');
    final period = local.hour >= 12 ? 'PM' : 'AM';

    return '${local.day.toString().padLeft(2, '0')}/'
        '${local.month.toString().padLeft(2, '0')}/'
        '${local.year} • $hour:$minute:$second $period';
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(30),
          ),
        ),
        padding: const EdgeInsets.fromLTRB(22, 12, 22, 20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              const SizedBox(height: 18),
              Container(
                width: 66,
                height: 66,
                decoration: const BoxDecoration(
                  color: Color(0xFFDCFCE7),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_rounded,
                  size: 40,
                  color: Color(0xFF16A34A),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Payment Successful',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF111827),
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Your transfer has been completed.',
                style: TextStyle(
                  fontSize: 13,
                  color: Color(0xFF6B7280),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                '₹${amount.toStringAsFixed(2)}',
                style: const TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF111827),
                ),
              ),
              const SizedBox(height: 18),
              _detailRow(
                icon: Icons.person_outline,
                label: 'Recipient',
                value: receiver,
              ),
              const Divider(height: 22),
              _detailRow(
                icon: Icons.account_circle_outlined,
                label: 'Sender',
                value: sender,
              ),
              const Divider(height: 22),
              _detailRow(
                icon: Icons.schedule_outlined,
                label: 'Payment Time',
                value: _formatDate(transactionDate),
              ),
              if (transactionId != null) ...[
                const Divider(height: 22),
                _detailRow(
                  icon: Icons.receipt_long_outlined,
                  label: 'Transaction ID',
                  value: transactionId.toString(),
                ),
              ],
              const Divider(height: 22),
              _detailRow(
                icon: Icons.verified_outlined,
                label: 'Status',
                value: 'Completed',
                valueColor: const Color(0xFF16A34A),
              ),
              if (balanceAfter != null) ...[
                const Divider(height: 22),
                _detailRow(
                  icon: Icons.account_balance_wallet_outlined,
                  label: 'Balance After Payment',
                  value: '₹${balanceAfter!.toStringAsFixed(2)}',
                ),
              ],
              const SizedBox(height: 22),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: onViewHistory,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF111827),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: const Text(
                    'View Transaction History',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton(
                  onPressed: onDone,
                  style: OutlinedButton.styleFrom(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  child: const Text('Done'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _detailRow({
    required IconData icon,
    required String label,
    required String value,
    Color? valueColor,
  }) {
    return Row(
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.05),
            shape: BoxShape.circle,
          ),
          child: Icon(
            icon,
            size: 20,
            color: const Color(0xFF374151),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF6B7280),
                ),
              ),
              const SizedBox(height: 3),
              Text(
                value,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: valueColor ?? const Color(0xFF111827),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
