import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:passkeys/authenticator.dart';
import 'package:passkeys/types.dart';

import '../../services/api_service.dart';
import '../home/home_screen.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // ============================================================
  // CONTROLLERS
  // ============================================================

  final TextEditingController _emailController =
      TextEditingController();

  final TextEditingController _passwordController =
      TextEditingController();

  // ============================================================
  // AUTHENTICATION
  // ============================================================

  final LocalAuthentication _localAuth =
      LocalAuthentication();

  final PasskeyAuthenticator _passkeyAuthenticator =
      PasskeyAuthenticator(
    debugMode: true,
  );

  // ============================================================
  // STATE
  // ============================================================

  static const int maxPasskeyFailures = 5;

  int _passkeyFailures = 0;

  bool _passwordVerified = false;
  bool _phoneAuthenticationVerified = false;

  bool _isPasskeyLoading = false;
  bool _isPasswordLoading = false;
  bool _isPhoneLoading = false;

  bool _obscurePassword = true;

  String? _errorMessage;

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();

    super.dispose();
  }

  // ============================================================
  // ERROR CLEANING
  // ============================================================

  String _cleanError(Object error) {
    String message = error.toString();

    if (message.startsWith('Exception: ')) {
      message = message.substring(11);
    }

    return message;
  }

  // ============================================================
  // PASSKEY AUTHENTICATION
  // ============================================================

  Future<Map<String, dynamic>?> _authenticatePasskey() async {
    final String email =
        _emailController.text.trim();

    if (email.isEmpty) {
      setState(() {
        _errorMessage =
            'Enter your Gmail address first.';
      });

      return null;
    }

    try {
      // ----------------------------------------------------------
      // 1. GET FRESH PASSKEY OPTIONS
      // ----------------------------------------------------------

      final Map<String, dynamic> optionsResult =
          await ApiService.getPasskeyLoginOptions(
        email: email,
      );

      // ----------------------------------------------------------
      // 2. CONVERT SERVER OPTIONS
      // ----------------------------------------------------------

      final String optionsJson =
          optionsResult['options'].toString();

      final AuthenticateRequestType request =
          AuthenticateRequestType.fromJsonString(
        optionsJson,
      );

      // ----------------------------------------------------------
      // 3. ANDROID PASSKEY
      // ----------------------------------------------------------

      final AuthenticateResponseType response =
          await _passkeyAuthenticator.authenticate(
        request,
      );

      // ----------------------------------------------------------
      // 4. SEND RESULT TO FASTAPI
      // ----------------------------------------------------------

      final Map<String, dynamic> credential =
          response.toJson();

      final dynamic rawStateId =
          optionsResult['state_id'];

      final int? stateId =
          rawStateId is int
              ? rawStateId
              : int.tryParse(
                  rawStateId?.toString() ?? '',
                );

      if (stateId == null) {
        throw Exception(
          'Invalid authentication state.',
        );
      }

      final Map<String, dynamic> result =
          await ApiService.verifyPasskeyLogin(
        stateId: stateId,
        credential: credential,
      );

      return result;
    } catch (e) {
      // IMPORTANT:
      // Any Passkey cancellation/failure is counted.
      return null;
    }
  }

  // ============================================================
  // NORMAL PASSKEY LOGIN
  // ============================================================

  Future<void> _startPasskeyLogin() async {
    final String email =
        _emailController.text.trim();

    if (email.isEmpty) {
      setState(() {
        _errorMessage =
            'Enter your Gmail address first.';
      });

      return;
    }

    if (_passkeyFailures >= maxPasskeyFailures) {
      setState(() {
        _errorMessage =
            'Five Passkey attempts have failed. '
            'Login password verification is required.';
      });

      return;
    }

    setState(() {
      _isPasskeyLoading = true;
      _errorMessage = null;
    });

    final Map<String, dynamic>? result =
        await _authenticatePasskey();

    if (!mounted) {
      return;
    }

    setState(() {
      _isPasskeyLoading = false;
    });

    // ----------------------------------------------------------
    // PASSKEY SUCCESS
    // ----------------------------------------------------------

    if (result != null) {
      _passkeyFailures = 0;

      await _finishSuccessfulLogin(result);

      return;
    }

    // ----------------------------------------------------------
    // PASSKEY FAILURE
    // ----------------------------------------------------------

    setState(() {
      _passkeyFailures++;

      if (_passkeyFailures >= maxPasskeyFailures) {
        _errorMessage =
            'Five Passkey attempts failed.\n\n'
            'Your Login Password is now required.';
      } else {
        _errorMessage =
            'Passkey verification failed.\n'
            'Attempt $_passkeyFailures of '
            '$maxPasskeyFailures.';
      }
    });
  }

  // ============================================================
  // VERIFY LOGIN PASSWORD
  // ============================================================

  Future<bool> _verifyLoginPassword() async {
    final String email =
        _emailController.text.trim();

    final String password =
        _passwordController.text;

    if (email.isEmpty) {
      setState(() {
        _errorMessage =
            'Enter your Gmail address.';
      });

      return false;
    }

    if (password.isEmpty) {
      setState(() {
        _errorMessage =
            'Enter your Login Password.';
      });

      return false;
    }

    setState(() {
      _isPasswordLoading = true;
      _errorMessage = null;
    });

    try {
      final Map<String, dynamic> result =
          await ApiService.login(
        email,
        password,
      );

      if (!mounted) {
        return false;
      }

      final bool passkeySet =
          result['passkey_set'] == true;

      if (!passkeySet) {
        setState(() {
          _isPasswordLoading = false;

          _errorMessage =
              'No Passkey is registered for this account. '
              'Complete Passkey setup first.';
        });

        return false;
      }

      setState(() {
        _passwordVerified = true;
        _isPasswordLoading = false;
        _errorMessage = null;
      });

      return true;
    } catch (e) {
      if (!mounted) {
        return false;
      }

      setState(() {
        _isPasswordLoading = false;
        _errorMessage = _cleanError(e);
      });

      return false;
    }
  }

  // ============================================================
  // PHONE PIN / BIOMETRIC
  // ============================================================

  Future<bool> _verifyPhoneAuthentication() async {
    setState(() {
      _isPhoneLoading = true;
      _errorMessage = null;
    });

    try {
      final bool supported =
          await _localAuth.isDeviceSupported();

      if (!supported) {
        if (!mounted) {
          return false;
        }

        setState(() {
          _isPhoneLoading = false;
          _errorMessage =
              'Phone PIN/biometric authentication '
              'is not supported on this device.';
        });

        return false;
      }

      final bool authenticated =
          await _localAuth.authenticate(
        localizedReason:
            'Verify your phone PIN, pattern, password, '
            'fingerprint, or face to continue',
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          useErrorDialogs: true,
          sensitiveTransaction: true,
        ),
      );

      if (!mounted) {
        return false;
      }

      if (!authenticated) {
        setState(() {
          _isPhoneLoading = false;
          _errorMessage =
              'Phone authentication failed.';
        });

        return false;
      }

      setState(() {
        _phoneAuthenticationVerified = true;
        _isPhoneLoading = false;
        _errorMessage = null;
      });

      return true;
    } catch (e) {
      if (!mounted) {
        return false;
      }

      setState(() {
        _isPhoneLoading = false;
        _errorMessage =
            'Phone authentication failed: '
            '${_cleanError(e)}';
      });

      return false;
    }
  }

  // ============================================================
  // FALLBACK AUTHENTICATION
  // ============================================================

  Future<void> _startFallbackAuthentication() async {
    // ----------------------------------------------------------
    // STEP 1 - LOGIN PASSWORD
    // ----------------------------------------------------------

    if (!_passwordVerified) {
      final bool passwordSuccess =
          await _verifyLoginPassword();

      if (!passwordSuccess || !mounted) {
        return;
      }
    }

    // ----------------------------------------------------------
    // STEP 2 - PHONE PIN / BIOMETRIC
    // ----------------------------------------------------------

    if (!_phoneAuthenticationVerified) {
      final bool phoneSuccess =
          await _verifyPhoneAuthentication();

      if (!phoneSuccess || !mounted) {
        return;
      }
    }

    // ----------------------------------------------------------
    // STEP 3 - FINAL PASSKEY
    // ----------------------------------------------------------

    setState(() {
      _isPasskeyLoading = true;
      _errorMessage = null;
    });

    final Map<String, dynamic>? result =
        await _authenticatePasskey();

    if (!mounted) {
      return;
    }

    setState(() {
      _isPasskeyLoading = false;
    });

    if (result == null) {
      setState(() {
        _errorMessage =
            'Final Passkey verification failed.\n'
            'Please try again.';
      });

      return;
    }

    await _finishSuccessfulLogin(result);
  }

  // ============================================================
  // COMPLETE LOGIN
  // ============================================================

  Future<void> _finishSuccessfulLogin(
    Map<String, dynamic> result,
  ) async {
    if (!mounted) {
      return;
    }

    final dynamic rawUserId =
        result['user_id'];

    final int? userId =
        rawUserId is int
            ? rawUserId
            : int.tryParse(
                rawUserId?.toString() ?? '',
              );

    if (userId == null) {
      setState(() {
        _errorMessage =
            'Invalid user information received '
            'from server.';
      });

      return;
    }

    final String userName =
        (result['name'] ?? 'User').toString();

    final String userEmail =
        (result['email'] ??
                _emailController.text.trim())
            .toString();

    final bool paymentPinSet =
        result['payment_pin_set'] == true;

    // ----------------------------------------------------------
    // PAYMENT PIN MUST ALREADY EXIST
    // ----------------------------------------------------------

    if (!paymentPinSet) {
      setState(() {
        _errorMessage =
            'Payment PIN is not configured for this account. '
            'Please complete Payment PIN setup first.';
      });

      return;
    }

    // ----------------------------------------------------------
    // OPEN HOME
    // ----------------------------------------------------------

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => HomeScreen(
          userId: userId,
          userName: userName,
          userEmail: userEmail,
        ),
      ),
    );
  }

  // ============================================================
  // RESET FALLBACK AUTHENTICATION
  // ============================================================

  void _resetAuthentication() {
    setState(() {
      _passkeyFailures = 0;

      _passwordVerified = false;

      _phoneAuthenticationVerified = false;

      _passwordController.clear();

      _errorMessage = null;
    });
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final bool fallbackRequired =
        _passkeyFailures >= maxPasskeyFailures;

    final bool busy =
        _isPasskeyLoading ||
        _isPasswordLoading ||
        _isPhoneLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('QuantumPay'),
        centerTitle: true,
      ),

      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),

          child: Column(
            crossAxisAlignment:
                CrossAxisAlignment.stretch,

            children: [
              const SizedBox(height: 25),

              // ==================================================
              // LOGO
              // ==================================================

              const Icon(
                Icons.account_balance_wallet,
                size: 70,
              ),

              const SizedBox(height: 18),

              const Text(
                'Welcome to QuantumPay',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 27,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 8),

              const Text(
                'Secure digital payments',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.grey,
                ),
              ),

              const SizedBox(height: 35),

              // ==================================================
              // EMAIL
              // ==================================================

              TextField(
                controller: _emailController,
                enabled: !busy,
                keyboardType:
                    TextInputType.emailAddress,
                textInputAction:
                    TextInputAction.next,
                decoration:
                    const InputDecoration(
                  labelText: 'Gmail',
                  hintText:
                      'example@gmail.com',
                  prefixIcon:
                      Icon(Icons.email_outlined),
                  border:
                      OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 25),

              // ==================================================
              // NORMAL PASSKEY LOGIN
              // ==================================================

              if (!fallbackRequired)
                Column(
                  children: [
                    SizedBox(
                      height: 54,
                      child:
                          ElevatedButton.icon(
                        onPressed:
                            busy
                                ? null
                                : _startPasskeyLogin,
                        icon:
                            _isPasskeyLoading
                                ? const SizedBox(
                                    width: 22,
                                    height: 22,
                                    child:
                                        CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(
                                    Icons.fingerprint,
                                  ),
                        label:
                            const Text(
                          'Use Passkey',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight:
                                FontWeight.bold,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 14),

                    if (_passkeyFailures > 0)
                      Text(
                        'Passkey attempts: '
                        '$_passkeyFailures / '
                        '$maxPasskeyFailures',
                        textAlign:
                            TextAlign.center,
                        style:
                            const TextStyle(
                          color:
                              Colors.orange,
                          fontWeight:
                              FontWeight.bold,
                        ),
                      ),
                  ],
                ),

              // ==================================================
              // FALLBACK AUTHENTICATION
              // ==================================================

              if (fallbackRequired)
                Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.stretch,

                  children: [
                    Container(
                      padding:
                          const EdgeInsets.all(16),

                      decoration:
                          BoxDecoration(
                        borderRadius:
                            BorderRadius.circular(12),

                        color:
                            Colors.orange.withValues(
                          alpha: 0.12,
                        ),
                      ),

                      child: const Column(
                        children: [
                          Icon(
                            Icons.security,
                            size: 40,
                          ),

                          SizedBox(height: 8),

                          Text(
                            'Additional verification required',
                            textAlign:
                                TextAlign.center,
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight:
                                  FontWeight.bold,
                            ),
                          ),

                          SizedBox(height: 6),

                          Text(
                            'Five Passkey attempts failed. '
                            'Complete the three verification steps.',
                            textAlign:
                                TextAlign.center,
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 25),

                    // ==================================================
                    // STEP 1
                    // ==================================================

                    const Text(
                      '1. Login Password',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 7),

                    const Text(
                      'Enter the Login Password that you '
                      'created during account registration.',
                    ),

                    const SizedBox(height: 12),

                    TextField(
                      controller:
                          _passwordController,

                      enabled:
                          !_passwordVerified &&
                          !_isPasswordLoading,

                      obscureText:
                          _obscurePassword,

                      textInputAction:
                          TextInputAction.done,

                      decoration:
                          InputDecoration(
                        labelText:
                            'Login Password',

                        hintText:
                            'Enter your Login Password',

                        prefixIcon:
                            const Icon(
                          Icons.lock_outline,
                        ),

                        suffixIcon:
                            IconButton(
                          onPressed: () {
                            setState(() {
                              _obscurePassword =
                                  !_obscurePassword;
                            });
                          },
                          icon:
                              Icon(
                            _obscurePassword
                                ? Icons.visibility_off
                                : Icons.visibility,
                          ),
                        ),

                        border:
                            const OutlineInputBorder(),
                      ),
                    ),

                    const SizedBox(height: 12),

                    if (!_passwordVerified)
                      SizedBox(
                        height: 50,
                        child:
                            ElevatedButton(
                          onPressed:
                              _isPasswordLoading
                                  ? null
                                  : _verifyLoginPassword,

                          child:
                              _isPasswordLoading
                                  ? const SizedBox(
                                      width: 22,
                                      height: 22,
                                      child:
                                          CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text(
                                      'Verify Login Password',
                                    ),
                        ),
                      ),

                    if (_passwordVerified)
                      const ListTile(
                        contentPadding:
                            EdgeInsets.zero,

                        leading:
                            Icon(
                          Icons.check_circle,
                          color:
                              Colors.green,
                        ),

                        title:
                            Text(
                          'Login Password verified',
                        ),
                      ),

                    const SizedBox(height: 25),

                    // ==================================================
                    // STEP 2
                    // ==================================================

                    const Text(
                      '2. Phone PIN / Biometric',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 7),

                    const Text(
                      'Verify using your Android phone PIN, '
                      'pattern, password, fingerprint, or face.',
                    ),

                    const SizedBox(height: 12),

                    if (!_phoneAuthenticationVerified)
                      SizedBox(
                        height: 50,
                        child:
                            ElevatedButton.icon(
                          onPressed:
                              !_passwordVerified ||
                                      _isPhoneLoading
                                  ? null
                                  : _verifyPhoneAuthentication,

                          icon:
                              const Icon(
                            Icons.phone_android,
                          ),

                          label:
                              _isPhoneLoading
                                  ? const SizedBox(
                                      width: 22,
                                      height: 22,
                                      child:
                                          CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text(
                                      'Verify Phone PIN / Biometric',
                                    ),
                        ),
                      ),

                    if (_phoneAuthenticationVerified)
                      const ListTile(
                        contentPadding:
                            EdgeInsets.zero,

                        leading:
                            Icon(
                          Icons.check_circle,
                          color:
                              Colors.green,
                        ),

                        title:
                            Text(
                          'Phone authentication verified',
                        ),
                      ),

                    const SizedBox(height: 25),

                    // ==================================================
                    // STEP 3
                    // ==================================================

                    const Text(
                      '3. Final Passkey',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 7),

                    const Text(
                      'Complete the final Passkey verification '
                      'to enter QuantumPay.',
                    ),

                    const SizedBox(height: 12),

                    SizedBox(
                      height: 50,
                      child:
                          ElevatedButton.icon(
                        onPressed:
                            !_passwordVerified ||
                                    !_phoneAuthenticationVerified ||
                                    _isPasskeyLoading
                                ? null
                                : _startFallbackAuthentication,

                        icon:
                            const Icon(
                          Icons.fingerprint,
                        ),

                        label:
                            _isPasskeyLoading
                                ? const SizedBox(
                                    width: 22,
                                    height: 22,
                                    child:
                                        CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Text(
                                    'Verify Final Passkey',
                                  ),
                      ),
                    ),

                    const SizedBox(height: 15),

                    OutlinedButton(
                      onPressed:
                          busy
                              ? null
                              : _resetAuthentication,

                      child:
                          const Text(
                        'Reset Authentication',
                      ),
                    ),
                  ],
                ),

              // ==================================================
              // ERROR MESSAGE
              // ==================================================

              if (_errorMessage != null)
                Container(
                  margin:
                      const EdgeInsets.only(
                    top: 20,
                  ),

                  padding:
                      const EdgeInsets.all(13),

                  decoration:
                      BoxDecoration(
                    borderRadius:
                        BorderRadius.circular(10),

                    color:
                        Colors.red.withValues(
                      alpha: 0.10,
                    ),
                  ),

                  child:
                      Text(
                    _errorMessage!,
                    textAlign:
                        TextAlign.center,

                    style:
                        const TextStyle(
                      color:
                          Colors.red,
                    ),
                  ),
                ),

              const SizedBox(height: 25),

              // ==================================================
              // REGISTER
              // ==================================================

              if (!fallbackRequired)
                TextButton(
                  onPressed:
                      busy
                          ? null
                          : () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) =>
                                      const RegisterScreen(),
                                ),
                              );
                            },

                  child:
                      const Text(
                    'Create a new QuantumPay account',
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}