import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000';

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

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Login failed',
    );
  }

  // =========================================================
  // GET WALLET
  // =========================================================

  static Future<Map<String, dynamic>> getWallet(
    int userId,
  ) async {
    final response = await http.get(
      Uri.parse('$baseUrl/wallet/$userId'),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to get wallet',
    );
  }

  // =========================================================
  // SEND MONEY
  // =========================================================

  static Future<Map<String, dynamic>> sendMoney({
    required int senderId,
    required String receiver,
    required double amount,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wallet/send'),
      headers: {
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'sender_id': senderId,
        'receiver': receiver,
        'amount': amount,
      }),
    );

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Money transfer failed',
    );
  }

  // =========================================================
  // RECEIVE MONEY
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

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Money receive failed',
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

    final data = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return data;
    }

    throw Exception(
      data['detail'] ?? 'Unable to get transactions',
    );
  }
  static Future<Map<String, dynamic>> register({
  required String name,
  required String email,
  required String phone,
  required String password,
}) async {
  final response = await http.post(
    Uri.parse('$baseUrl/register'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'name': name,
      'email': email,
      'phone': phone,
      'password': password,
    }),
  );

  final data = jsonDecode(response.body);

  if (response.statusCode == 200 || response.statusCode == 201) {
    return data;
  }

  throw Exception(data['detail'] ?? 'Registration failed');
}
}