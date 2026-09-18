import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_service.dart';
import '../payment/send_money_screen.dart';
import '../payment/receive_money_screen.dart';
import '../history/history_screen.dart';

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
  // ---------------------------------------------------------
  // BALANCE
  // ---------------------------------------------------------

  double _balance = 0.0;

  bool _isLoadingBalance = true;
  bool _balanceVisible = false;

  // ---------------------------------------------------------
  // PASSWORD PANEL
  // ---------------------------------------------------------

  bool _showPasswordPanel = false;

  final TextEditingController _passwordController =
      TextEditingController();

  bool _obscurePassword = true;

  String? _passwordError;

  // ---------------------------------------------------------
  // INIT
  // ---------------------------------------------------------

  @override
  void initState() {
    super.initState();

    _loadBalance();
  }

  // ---------------------------------------------------------
  // DISPOSE
  // ---------------------------------------------------------

  @override
  void dispose() {
    _passwordController.dispose();

    super.dispose();
  }

  // ---------------------------------------------------------
  // LOAD BALANCE FROM BACKEND
  // ---------------------------------------------------------

  Future<void> _loadBalance() async {
    try {
      final data = await ApiService.getWallet(
        widget.userId,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _balance = (data['balance'] as num).toDouble();
        _isLoadingBalance = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isLoadingBalance = false;
      });

      _showMessage(
        'Cannot connect to QuantumPay server',
      );
    }
  }

  // ---------------------------------------------------------
  // REFRESH BALANCE
  // ---------------------------------------------------------

  Future<void> _refreshBalance() async {
    setState(() {
      _isLoadingBalance = true;
    });

    await _loadBalance();
  }

  // ---------------------------------------------------------
  // OPEN PASSWORD PANEL
  // ---------------------------------------------------------

  void _openPasswordPanel() {
    setState(() {
      _showPasswordPanel = true;
      _passwordError = null;
      _passwordController.clear();
    });
  }

  // ---------------------------------------------------------
  // CLOSE PASSWORD PANEL
  // ---------------------------------------------------------

  void _closePasswordPanel() {
    FocusScope.of(context).unfocus();

    setState(() {
      _showPasswordPanel = false;
      _passwordError = null;
      _passwordController.clear();
    });
  }

  // ---------------------------------------------------------
  // VERIFY PASSWORD AND SHOW BALANCE
  // ---------------------------------------------------------

  Future<void> _unlockBalance() async {
    final password = _passwordController.text.trim();

    if (password.isEmpty) {
      setState(() {
        _passwordError = 'Please enter your password';
      });

      return;
    }

    try {
      // Verify the actual logged-in user's password
      await ApiService.login(
        widget.userEmail,
        password,
      );

      if (!mounted) {
        return;
      }

      FocusScope.of(context).unfocus();

      setState(() {
        _balanceVisible = true;
        _showPasswordPanel = false;
        _passwordError = null;
        _passwordController.clear();
      });

      _showMessage(
        'Balance unlocked',
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _passwordError = 'Incorrect password';
      });
    }
  }

  // ---------------------------------------------------------
  // HIDE BALANCE
  // ---------------------------------------------------------

  void _hideBalance() {
    setState(() {
      _balanceVisible = false;
    });
  }

  // ---------------------------------------------------------
  // MESSAGE
  // ---------------------------------------------------------

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).hideCurrentSnackBar();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
      ),
    );
  }

  // ---------------------------------------------------------
  // FORMAT BALANCE
  // ---------------------------------------------------------

  String _formattedBalance() {
    return '₹ ${_balance.toStringAsFixed(2)}';
  }

  // ---------------------------------------------------------
  // OPEN SEND MONEY
  // ---------------------------------------------------------

  Future<void> _openSendMoney() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => SendMoneyScreen(
          userId: widget.userId,
          userEmail: widget.userEmail,
        ),
      ),
    );

    // Always hide balance after returning
    if (!mounted) {
      return;
    }

    setState(() {
      _balanceVisible = false;
    });

    // Refresh only when a transaction was completed
    if (result == true) {
      await _refreshBalance();
    }
  }

  // ---------------------------------------------------------
  // OPEN RECEIVE MONEY
  // ---------------------------------------------------------

  Future<void> _openReceiveMoney() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ReceiveMoneyScreen(
          userId: widget.userId,
        ),
      ),
    );

    // Always hide balance after returning
    if (!mounted) {
      return;
    }

    setState(() {
      _balanceVisible = false;
    });

    // Refresh only when a transaction was completed
    if (result == true) {
      await _refreshBalance();
    }
  }

  // ---------------------------------------------------------
  // OPEN HISTORY
  // ---------------------------------------------------------

  Future<void> _openHistory() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => HistoryScreen(
          userId: widget.userId,
        ),
      ),
    );

    // Keep balance hidden when returning
    if (!mounted) {
      return;
    }

    setState(() {
      _balanceVisible = false;
    });
  }

  // ---------------------------------------------------------
  // BUILD
  // ---------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'QuantumPay',
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh Balance',
            onPressed: _refreshBalance,
            icon: const Icon(
              Icons.refresh,
            ),
          ),
        ],
      ),

      // -------------------------------------------------------
      // BODY
      // -------------------------------------------------------

      body: RefreshIndicator(
        onRefresh: _refreshBalance,

        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),

          padding: const EdgeInsets.all(20),

          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,

            children: [
              // =================================================
              // GREETING
              // =================================================

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

              // =================================================
              // BALANCE CARD
              // =================================================

              Container(
                width: double.infinity,

                padding: const EdgeInsets.all(24),

                decoration: BoxDecoration(
                  color: AppColors.primary,

                  borderRadius: BorderRadius.circular(22),

                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(
                        alpha: 0.08,
                      ),
                      blurRadius: 12,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),

                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,

                  children: [
                    // -----------------------------
                    // BALANCE TITLE
                    // -----------------------------

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
                              : _openPasswordPanel,

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

                    // -----------------------------
                    // BALANCE
                    // -----------------------------

                    if (_isLoadingBalance)
                      const SizedBox(
                        height: 42,

                        child: Align(
                          alignment: Alignment.centerLeft,

                          child: SizedBox(
                            width: 25,
                            height: 25,

                            child:
                                CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2.5,
                            ),
                          ),
                        ),
                      )
                    else
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
                          : 'Password required to view balance',

                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 15),

              // =================================================
              // PASSWORD PANEL
              // =================================================

              if (_showPasswordPanel)
                Container(
                  width: double.infinity,

                  padding: const EdgeInsets.all(20),

                  decoration: BoxDecoration(
                    color: Colors.white,

                    borderRadius:
                        BorderRadius.circular(18),

                    border: Border.all(
                      color: AppColors.primary.withValues(
                        alpha: 0.2,
                      ),
                    ),

                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(
                          alpha: 0.06,
                        ),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),

                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,

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
                        'Enter your password to view your balance.',

                        style: TextStyle(
                          fontSize: 13,
                          color: AppColors.textSecondary,
                        ),
                      ),

                      const SizedBox(height: 16),

                      TextField(
                        controller: _passwordController,

                        obscureText: _obscurePassword,

                        keyboardType:
                            TextInputType.number,

                        decoration: InputDecoration(
                          labelText: 'Password',

                          prefixIcon:
                              const Icon(
                            Icons.lock_outline,
                          ),

                          errorText: _passwordError,

                          suffixIcon: IconButton(
                            onPressed: () {
                              setState(() {
                                _obscurePassword =
                                    !_obscurePassword;
                              });
                            },

                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                          ),
                        ),

                        onSubmitted: (_) {
                          _unlockBalance();
                        },
                      ),

                      const SizedBox(height: 16),

                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed:
                                  _closePasswordPanel,

                              child:
                                  const Text(
                                'Cancel',
                              ),
                            ),
                          ),

                          const SizedBox(width: 12),

                          Expanded(
                            child: ElevatedButton(
                              onPressed:
                                  _unlockBalance,

                              child:
                                  const Text(
                                'Unlock',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 30),

              // =================================================
              // QUICK ACTIONS
              // =================================================

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
                  // -----------------------------
                  // SEND
                  // -----------------------------

                  _ActionButton(
                    icon: Icons.send,
                    title: 'Send',
                    onTap: _openSendMoney,
                  ),

                  // -----------------------------
                  // RECEIVE
                  // -----------------------------

                  _ActionButton(
                    icon: Icons.call_received,
                    title: 'Receive',
                    onTap: _openReceiveMoney,
                  ),

                  // -----------------------------
                  // HISTORY
                  // -----------------------------

                  _ActionButton(
                    icon: Icons.history,
                    title: 'History',
                    onTap: _openHistory,
                  ),
                ],
              ),

              const SizedBox(height: 35),

              // =================================================
              // ACCOUNT INFORMATION
              // =================================================

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

                  borderRadius:
                      BorderRadius.circular(18),

                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(
                        alpha: 0.05,
                      ),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),

                child: Column(
                  children: [
                    // NAME
                    _AccountRow(
                      icon: Icons.person_outline,
                      title: 'Name',
                      value: widget.userName,
                    ),

                    const Divider(),

                    // EMAIL
                    _AccountRow(
                      icon: Icons.email_outlined,
                      title: 'Email',
                      value: widget.userEmail,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 30),

              // =================================================
              // BACKEND STATUS
              // =================================================

              Center(
                child: Row(
                  mainAxisAlignment:
                      MainAxisAlignment.center,

                  children: const [
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

// =============================================================
// ACTION BUTTON
// =============================================================

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
            width: 65,
            height: 65,

            decoration: BoxDecoration(
              color: AppColors.white,

              borderRadius:
                  BorderRadius.circular(16),

              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(
                    alpha: 0.05,
                  ),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                ),
              ],
            ),

            child: Icon(
              icon,
              color: AppColors.primary,
              size: 28,
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

// =============================================================
// ACCOUNT ROW
// =============================================================

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
      padding: const EdgeInsets.symmetric(
        vertical: 8,
      ),

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