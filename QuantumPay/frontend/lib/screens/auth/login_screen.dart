import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../home/home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // ---------------------------------------------------------
  // CONTROLLERS
  // ---------------------------------------------------------

  final TextEditingController _emailController =
      TextEditingController();

  final TextEditingController _passwordController =
      TextEditingController();

  // ---------------------------------------------------------
  // STATE
  // ---------------------------------------------------------

  bool _isLoading = false;
  bool _obscurePassword = true;

  String? _errorMessage;

  // ---------------------------------------------------------
  // DISPOSE
  // ---------------------------------------------------------

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();

    super.dispose();
  }

  // ---------------------------------------------------------
  // LOGIN
  // ---------------------------------------------------------

  Future<void> _login() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    // Clear previous error
    setState(() {
      _errorMessage = null;
    });

    // Validate email
    if (email.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your email';
      });
      return;
    }

    // Validate password
    if (password.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your password';
      });
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // -------------------------------------------------------
      // CALL FASTAPI LOGIN
      // -------------------------------------------------------

      final result = await ApiService.login(
        email,
        password,
      );

      if (!mounted) {
        return;
      }

      // -------------------------------------------------------
      // GET USER INFORMATION FROM BACKEND
      // -------------------------------------------------------

      final int userId = result['user_id'];

      final String userName =
          result['name'] ?? 'User';

      final String userEmail =
          result['email'] ?? email;

      // -------------------------------------------------------
      // GO TO HOME
      // -------------------------------------------------------

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => HomeScreen(
            userId: userId,
            userName: userName,
            userEmail: userEmail,
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

      setState(() {
        _errorMessage = message;
        _isLoading = false;
      });

      return;
    }

    if (mounted) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // ---------------------------------------------------------
  // BUILD
  // ---------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),

          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,

            children: [
              const SizedBox(height: 50),

              // =================================================
              // LOGO / TITLE
              // =================================================

              Center(
                child: Column(
                  children: [
                    Container(
                      width: 80,
                      height: 80,

                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .primary,

                        borderRadius:
                            BorderRadius.circular(22),
                      ),

                      child: const Icon(
                        Icons.account_balance_wallet,
                        color: Colors.white,
                        size: 42,
                      ),
                    ),

                    const SizedBox(height: 18),

                    const Text(
                      'QuantumPay',

                      style: TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 6),

                    const Text(
                      'Secure digital payments',

                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 45),

              // =================================================
              // LOGIN TITLE
              // =================================================

              const Text(
                'Welcome Back',

                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 8),

              const Text(
                'Login to continue to your QuantumPay account.',

                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 14,
                ),
              ),

              const SizedBox(height: 28),

              // =================================================
              // EMAIL
              // =================================================

              TextField(
                controller: _emailController,

                keyboardType:
                    TextInputType.emailAddress,

                textInputAction:
                    TextInputAction.next,

                decoration: const InputDecoration(
                  labelText: 'Email',

                  hintText:
                      'Enter your email',

                  prefixIcon:
                      Icon(Icons.email_outlined),

                  border:
                      OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 18),

              // =================================================
              // PASSWORD
              // =================================================

              TextField(
                controller: _passwordController,

                obscureText: _obscurePassword,

                textInputAction:
                    TextInputAction.done,

                onSubmitted: (_) {
                  if (!_isLoading) {
                    _login();
                  }
                },

                decoration: InputDecoration(
                  labelText: 'Password',

                  hintText:
                      'Enter your password',

                  prefixIcon:
                      const Icon(Icons.lock_outline),

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

                  border:
                      const OutlineInputBorder(),
                ),
              ),

              // =================================================
              // ERROR MESSAGE
              // =================================================

              if (_errorMessage != null) ...[
                const SizedBox(height: 14),

                Container(
                  width: double.infinity,

                  padding:
                      const EdgeInsets.all(12),

                  decoration: BoxDecoration(
                    color: Colors.red.withValues(
                      alpha: 0.08,
                    ),

                    borderRadius:
                        BorderRadius.circular(10),
                  ),

                  child: Row(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,

                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: Colors.red,
                        size: 20,
                      ),

                      const SizedBox(width: 8),

                      Expanded(
                        child: Text(
                          _errorMessage!,

                          style:
                              const TextStyle(
                            color: Colors.red,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 28),

              // =================================================
              // LOGIN BUTTON
              // =================================================

              SizedBox(
                width: double.infinity,
                height: 54,

                child: ElevatedButton(
                  onPressed:
                      _isLoading ? null : _login,

                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,

                          child:
                              CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : const Text(
                          'Login',

                          style: TextStyle(
                            fontSize: 16,
                            fontWeight:
                                FontWeight.bold,
                          ),
                        ),
                ),
              ),

              const SizedBox(height: 25),

              // =================================================
              // BACKEND INFO
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
                      'Secure backend login',

                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 30),
            ],
          ),
        ),
      ),
    );
  }
}