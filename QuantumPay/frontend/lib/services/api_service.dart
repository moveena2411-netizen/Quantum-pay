import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiService {
  // =========================================================
  // BACKEND URL
  // =========================================================

  // Physical Android phone and PC are on the same Wi-Fi network.
  static const String baseUrl = 'http://192.168.1.3:8000';

  // =========================================================
  // COMMON RESPONSE PARSER
  // =========================================================

  static Map<String, dynamic> _jsonMap(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);

      if (decoded is Map<String, dynamic>) {
        return decoded;
      }

      return {
        'detail': 'Unexpected server response',
      };
    } catch (_) {
      return {
        'detail': 'Invalid server response',
      };
    }
  }

  // =========================================================
  // LOGIN
  // =========================================================

  static Future<Map<String, dynamic>> login(
    String email,
    String password,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Login failed',
    );
  }

  // =========================================================
  // REGISTER
  // =========================================================

  static Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String phone,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/register'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'name': name,
        'email': email,
        'phone': phone,
        'password': password,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Registration failed',
    );
  }

  // =========================================================
  // PAYMENT PIN SETUP
  // =========================================================

  static Future<Map<String, dynamic>> setupPaymentPin({
    required int userId,
    required String loginPassword,
    required String paymentPin,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/payment-pin/setup'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_id': userId,
        'login_password': loginPassword,
        'payment_pin': paymentPin,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Payment PIN setup failed',
    );
  }

  // =========================================================
  // PAYMENT PIN VERIFY
  // =========================================================

  static Future<Map<String, dynamic>> verifyPaymentPin({
    required int userId,
    required String paymentPin,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/payment-pin/verify'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_id': userId,
        'payment_pin': paymentPin,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Incorrect Payment PIN',
    );
  }

  // =========================================================
  // VIEW BALANCE WITH PAYMENT PIN
  // =========================================================

  static Future<Map<String, dynamic>> getBalanceWithPin({
    required int userId,
    required String paymentPin,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wallet/balance'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_id': userId,
        'payment_pin': paymentPin,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to view balance',
    );
  }

  // =========================================================
  // WALLET METADATA / LEGACY COMPATIBILITY
  // =========================================================

  static Future<Map<String, dynamic>> getWallet(
    int userId,
  ) async {
    final response = await http.get(
      Uri.parse('$baseUrl/wallet/$userId'),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to get wallet',
    );
  }

  // =========================================================
  // SEND MONEY WITH PAYMENT PIN
  // =========================================================

  static Future<Map<String, dynamic>> sendMoney({
    required int senderId,
    required String receiver,
    required double amount,
    required String paymentPin,
    String? message,
  }) async {
    final body = <String, dynamic>{
      'sender_id': senderId,
      'receiver': receiver,
      'amount': amount,
      'payment_pin': paymentPin,

      // Optional transaction note.
      // It is NOT analyzed as an incoming security message.
      'message': message?.trim() ?? '',
    };

    final response = await http.post(
      Uri.parse('$baseUrl/wallet/send'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );

    final data = _jsonMap(response);

    // HTTP 200 is also used by the backend for
    // CHALLENGE_REQUIRED.
    //
    // The caller must inspect:
    // data['status']
    //
    // before showing transaction success.
    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Money transfer failed',
    );
  }

  // =========================================================
  // CHALLENGE QUESTIONS
  // =========================================================

  static Future<List<dynamic>> getChallengeQuestions() async {
    final response = await http.get(
      Uri.parse('$baseUrl/risk/challenge/questions'),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      final questions = data['questions'];

      if (questions is List<dynamic>) {
        return questions;
      }
    }

    throw Exception(
      data['detail'] ?? 'Unable to load security challenge',
    );
  }

  // =========================================================
  // COMPLETE HIGH-RISK CHALLENGE
  // =========================================================

  static Future<Map<String, dynamic>> completeChallenge({
    required int pendingTransactionId,
    required Map<String, bool> answers,
    required String paymentPin,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wallet/challenge/complete'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'pending_transaction_id': pendingTransactionId,
        'answers': answers,
        'payment_pin': paymentPin,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Security challenge failed',
    );
  }

  // =========================================================
  // DISABLED RECEIVE MONEY - LEGACY COMPATIBILITY
  // =========================================================

  static Future<Map<String, dynamic>> receiveMoney({
    required int userId,
    required double amount,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wallet/receive'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_id': userId,
        'amount': amount,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Receive Money is disabled',
    );
  }

  // =========================================================
  // TRANSACTION HISTORY
  // =========================================================

  static Future<List<dynamic>> getTransactions(
    int userId,
  ) async {
    final response = await http.get(
      Uri.parse('$baseUrl/transactions/$userId'),
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);

      if (decoded is List<dynamic>) {
        return decoded;
      }
    }

    final data = _jsonMap(response);

    throw Exception(
      data['detail'] ?? 'Unable to get transactions',
    );
  }

  // =========================================================
  // PASSKEY REGISTRATION OPTIONS
  // =========================================================

  static Future<Map<String, dynamic>>
      getPasskeyRegistrationOptions({
    required int userId,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/passkey/register/options'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_id': userId,
        'password': password,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to start passkey registration',
    );
  }

  // =========================================================
  // PASSKEY REGISTRATION VERIFY
  // =========================================================

  static Future<Map<String, dynamic>>
      verifyPasskeyRegistration({
    required int stateId,
    required Map<String, dynamic> credential,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/passkey/register/verify'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'state_id': stateId,
        'credential': credential,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Passkey registration failed',
    );
  }

  // =========================================================
  // PASSKEY LOGIN OPTIONS
  // =========================================================

  static Future<Map<String, dynamic>>
      getPasskeyLoginOptions({
    required String email,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/passkey/login/options'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'email': email,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to start passkey login',
    );
  }

  // =========================================================
  // PASSKEY LOGIN VERIFY
  // =========================================================

  static Future<Map<String, dynamic>> verifyPasskeyLogin({
    required int stateId,
    required Map<String, dynamic> credential,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/passkey/login/verify'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'state_id': stateId,
        'credential': credential,
      }),
    );

    final data = _jsonMap(response);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Passkey login failed',
    );
  }
}