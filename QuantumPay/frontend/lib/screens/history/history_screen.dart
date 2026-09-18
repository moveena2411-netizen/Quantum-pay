import 'package:flutter/material.dart';

import '../../services/api_service.dart';

class HistoryScreen extends StatefulWidget {
  final int userId;

  const HistoryScreen({
    super.key,
    required this.userId,
  });

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> _transactions = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  // =========================================================
  // LOAD TRANSACTIONS FROM BACKEND
  // =========================================================

  Future<void> _loadTransactions() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final transactions =
          await ApiService.getTransactions(widget.userId);

      if (!mounted) return;

      setState(() {
        _transactions = transactions;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceFirst(
              'Exception: ',
              '',
            );
      });
    }
  }

  // =========================================================
  // FORMAT DATE & TIME
  // =========================================================

  String _formatDateTime(String timestamp) {
    try {
      DateTime dateTime = DateTime.parse(timestamp);

      // Backend timestamps are normally returned in UTC.
      // Convert UTC to the device's local timezone.
      if (dateTime.isUtc) {
        dateTime = dateTime.toLocal();
      } else {
        // If the backend sends a timestamp without timezone
        // information, treat it as UTC and then convert it.
        dateTime = DateTime.utc(
          dateTime.year,
          dateTime.month,
          dateTime.day,
          dateTime.hour,
          dateTime.minute,
          dateTime.second,
          dateTime.millisecond,
          dateTime.microsecond,
        ).toLocal();
      }

      final day = dateTime.day.toString().padLeft(2, '0');
      final month = dateTime.month.toString().padLeft(2, '0');
      final year = dateTime.year.toString();

      final hour = dateTime.hour % 12 == 0
          ? 12
          : dateTime.hour % 12;

      final minute =
          dateTime.minute.toString().padLeft(2, '0');

      final period = dateTime.hour >= 12 ? 'PM' : 'AM';

      return '$day/$month/$year • $hour:$minute $period';
    } catch (_) {
      return timestamp;
    }
  }

  // =========================================================
  // CHECK WHETHER TRANSACTION IS SENT
  // =========================================================

  bool _isSent(Map<String, dynamic> transaction) {
    final type =
        transaction['transaction_type']
            ?.toString()
            .toUpperCase();

    return type == 'SEND';
  }

  // =========================================================
  // TRANSACTION CARD
  // =========================================================

  Widget _buildTransactionCard(
    Map<String, dynamic> transaction,
  ) {
    final bool isSent = _isSent(transaction);

    final double amount =
        double.tryParse(
              transaction['amount']?.toString() ?? '0',
            ) ??
            0.0;

    final String sender =
        transaction['sender']?.toString() ?? 'Unknown';

    final String receiver =
        transaction['receiver']?.toString() ?? 'Unknown';

    final String timestamp =
        transaction['timestamp']?.toString() ?? '';

    // For SEND → show receiver
    // For RECEIVE → show sender
    final String person =
        isSent ? receiver : sender;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // =================================================
            // ICON
            // =================================================

            CircleAvatar(
              radius: 25,
              child: Icon(
                isSent
                    ? Icons.arrow_upward
                    : Icons.arrow_downward,
              ),
            ),

            const SizedBox(width: 14),

            // =================================================
            // TRANSACTION DETAILS
            // =================================================

            Expanded(
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Text(
                    isSent
                        ? 'Money Sent'
                        : 'Money Received',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  const SizedBox(height: 5),

                  Text(
                    person,
                    style: const TextStyle(
                      fontSize: 14,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),

                  const SizedBox(height: 5),

                  Text(
                    _formatDateTime(timestamp),
                    style: const TextStyle(
                      fontSize: 12,
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 8),

            // =================================================
            // AMOUNT
            // =================================================

            Text(
              '${isSent ? '- ' : '+ '}₹${amount.toStringAsFixed(2)}',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color:
                    isSent ? Colors.red : Colors.green,
              ),
            ),
          ],
        ),
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
        title: const Text(
          'Transaction History',
        ),
      ),

      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(),
            )

          : _errorMessage != null
              ? Center(
                  child: Padding(
                    padding:
                        const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize:
                          MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.error_outline,
                          size: 50,
                          color: Colors.red,
                        ),

                        const SizedBox(height: 12),

                        Text(
                          _errorMessage!,
                          textAlign:
                              TextAlign.center,
                        ),

                        const SizedBox(height: 16),

                        ElevatedButton(
                          onPressed:
                              _loadTransactions,
                          child:
                              const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )

              : _transactions.isEmpty
                  ? RefreshIndicator(
                      onRefresh:
                          _loadTransactions,
                      child: ListView(
                        physics:
                            const AlwaysScrollableScrollPhysics(),
                        children: const [
                          SizedBox(height: 250),
                          Center(
                            child: Text(
                              'No transactions yet',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.grey,
                              ),
                            ),
                          ),
                        ],
                      ),
                    )

                  : RefreshIndicator(
                      onRefresh:
                          _loadTransactions,
                      child: ListView.builder(
                        physics:
                            const AlwaysScrollableScrollPhysics(),
                        padding:
                            const EdgeInsets.all(16),
                        itemCount:
                            _transactions.length,
                        itemBuilder:
                            (context, index) {
                          final transaction =
                              Map<String, dynamic>.from(
                            _transactions[index],
                          );

                          return _buildTransactionCard(
                            transaction,
                          );
                        },
                      ),
                    ),
    );
  }
}