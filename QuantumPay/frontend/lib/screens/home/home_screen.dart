import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_service.dart';
import '../history/history_screen.dart';
import '../payment/send_money_screen.dart';

class HomeScreen extends StatefulWidget {
  final int userId;
  final String userName;
  final String userEmail;

  const HomeScreen({
    super.key,
    required this.userId,
    required this.userName,
    required this.userEmail,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  double _balance = 0.0;
  bool _balanceVisible = false;
  bool _showPinPanel = false;
  bool _isVerifyingPin = false;

  final TextEditingController _pinController =
      TextEditingController();

  String? _pinError;

  @override
  void dispose() {
    _pinController.dispose();
    super.dispose();
  }

  void _openPinPanel() {
    setState(() {
      _showPinPanel = true;
      _pinError = null;
      _pinController.clear();
    });
  }

  void _closePinPanel() {
    FocusScope.of(context).unfocus();

    setState(() {
      _showPinPanel = false;
      _pinError = null;
      _pinController.clear();
    });
  }

  Future<void> _verifyPinAndShowBalance() async {
    final pin = _pinController.text.trim();

    if (!RegExp(r'^\d{6}$').hasMatch(pin)) {
      setState(() {
        _pinError = 'Enter exactly 6 digits';
      });
      return;
    }

    setState(() {
      _isVerifyingPin = true;
      _pinError = null;
    });

    try {
      final result = await ApiService.getBalanceWithPin(
        userId: widget.userId,
        paymentPin: pin,
      );

      if (!mounted) {
        return;
      }

      final balanceValue = result['balance'];

      setState(() {
        _balance = (balanceValue as num).toDouble();
        _balanceVisible = true;
        _showPinPanel = false;
        _isVerifyingPin = false;
        _pinController.clear();
      });

      FocusScope.of(context).unfocus();
    } catch (e) {
      if (!mounted) {
        return;
      }

      String message = e.toString();

      if (message.startsWith('Exception: ')) {
        message = message.substring(11);
      }

      setState(() {
        _isVerifyingPin = false;
        _pinError = message;
      });
    }
  }

  void _hideBalance() {
    setState(() {
      _balanceVisible = false;
    });
  }

  Future<void> _openHistory() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => HistoryScreen(
          userId: widget.userId,
          userEmail: widget.userEmail,
        ),
      ),
    );
  }

  Future<void> _openSendMoney() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => SendMoneyScreen(
          userId: widget.userId,
          userEmail: widget.userEmail,
        ),
      ),
    );

    if (!mounted) {
      return;
    }

    setState(() {
      _balanceVisible = false;
      _showPinPanel = false;
      _pinController.clear();
    });
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  String _formattedBalance() {
    return '₹ ${_balance.toStringAsFixed(2)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('QuantumPay'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () {
              setState(() {
                _balanceVisible = false;
              });
              _showMessage('Balance is hidden. Enter PIN to view it.');
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          setState(() {
            _balanceVisible = false;
          });
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Hello, ${widget.userName} 👋',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),

              const SizedBox(height: 6),

              const Text(
                'Welcome back to QuantumPay',
                style: TextStyle(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),

              const SizedBox(height: 25),

              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.08),
                      blurRadius: 12,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Available Balance',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 15,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed: _balanceVisible
                              ? _hideBalance
                              : _openPinPanel,
                          icon: Icon(
                            _balanceVisible
                                ? Icons.visibility
                                : Icons.visibility_off,
                            color: Colors.white,
                            size: 25,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 5),

                    Text(
                      _balanceVisible
                          ? _formattedBalance()
                          : '₹ ••••••••',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 8),

                    Text(
                      _balanceVisible
                          ? 'Tap the eye icon to hide'
                          : '6-digit Payment PIN required',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 15),

              if (_showPinPanel)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: AppColors.primary.withValues(alpha: 0.2),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Unlock Balance',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 6),

                      const Text(
                        'Enter your 6-digit Payment PIN to view your balance.',
                        style: TextStyle(
                          fontSize: 13,
                          color: AppColors.textSecondary,
                        ),
                      ),

                      const SizedBox(height: 16),

                      TextField(
                        controller: _pinController,
                        obscureText: true,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        decoration: InputDecoration(
                          labelText: 'Payment PIN',
                          prefixIcon: const Icon(Icons.pin_outlined),
                          errorText: _pinError,
                          counterText: '',
                          border: const OutlineInputBorder(),
                        ),
                        onSubmitted: (_) =>
                            _verifyPinAndShowBalance(),
                      ),

                      const SizedBox(height: 16),

                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _isVerifyingPin
                                  ? null
                                  : _closePinPanel,
                              child: const Text('Cancel'),
                            ),
                          ),

                          const SizedBox(width: 12),

                          Expanded(
                            child: ElevatedButton(
                              onPressed: _isVerifyingPin
                                  ? null
                                  : _verifyPinAndShowBalance,
                              child: _isVerifyingPin
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child:
                                          CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white,
                                      ),
                                    )
                                  : const Text('Unlock'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 30),

              const Text(
                'Quick Actions',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),

              const SizedBox(height: 20),

              Row(
                mainAxisAlignment:
                    MainAxisAlignment.spaceAround,
                children: [
                  _ActionButton(
                    icon: Icons.send,
                    title: 'Send',
                    onTap: _openSendMoney,
                  ),
                  _ActionButton(
                    icon: Icons.history,
                    title: 'History',
                    onTap: _openHistory,
                  ),
                ],
              ),

              const SizedBox(height: 35),

              const Text(
                'Account',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 15),

              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    _AccountRow(
                      icon: Icons.person_outline,
                      title: 'Name',
                      value: widget.userName,
                    ),

                    const Divider(),

                    _AccountRow(
                      icon: Icons.email_outlined,
                      title: 'Email',
                      value: widget.userEmail,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 30),

              const Center(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.cloud_done,
                      size: 16,
                      color: Colors.green,
                    ),
                    SizedBox(width: 6),
                    Text(
                      'QuantumPay Backend Connected',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Column(
        children: [
          Container(
            width: 70,
            height: 70,
            decoration: BoxDecoration(
              color: AppColors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.05),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Icon(
              icon,
              color: AppColors.primary,
              size: 30,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _AccountRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _AccountRow({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(
            icon,
            color: AppColors.primary,
            size: 22,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
