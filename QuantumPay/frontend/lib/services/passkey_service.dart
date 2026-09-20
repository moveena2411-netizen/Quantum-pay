import 'dart:convert';

import 'package:passkeys/authenticator.dart';
import 'package:passkeys/types.dart';

class PasskeyService {
  // --------------------------------------------------
  // RELYING PARTY ID
  // --------------------------------------------------

  static const String relyingPartyId =
      'squeak-crablike-walnut.ngrok-free.dev';

  // --------------------------------------------------
  // PASSKEY AUTHENTICATOR
  // --------------------------------------------------

  final PasskeyAuthenticator authenticator =
      PasskeyAuthenticator(
    debugMode: true,
  );

  // --------------------------------------------------
  // CHECK PASSKEY SUPPORT
  // --------------------------------------------------

  Future<bool> isSupported() async {
    final availability =
        await authenticator.getAvailability().android();

    return availability.hasPasskeySupport;
  }

  // --------------------------------------------------
  // REGISTER PASSKEY
  // --------------------------------------------------

  Future<Map<String, dynamic>> registerPasskey({
    required String optionsJson,
  }) async {
    final RegisterRequestType request =
        RegisterRequestType.fromJsonString(
      optionsJson,
    );

    final RegisterResponseType response =
        await authenticator.register(
      request,
    );

    return response.toJson();
  }

  // --------------------------------------------------
  // AUTHENTICATE WITH PASSKEY
  // --------------------------------------------------

  Future<Map<String, dynamic>> authenticateWithPasskey({
    required String optionsJson,
  }) async {
    // -----------------------------------------------
    // Decode the server options.
    // -----------------------------------------------

    final dynamic decoded =
        jsonDecode(optionsJson);

    if (decoded is! Map<String, dynamic>) {
      throw Exception(
        'Invalid passkey authentication options.',
      );
    }

    final Map<String, dynamic> options =
        Map<String, dynamic>.from(decoded);

    // -----------------------------------------------
    // The current passkeys Flutter package requires
    // "transports" to be a list for every credential.
    //
    // py_webauthn may omit this field when no transport
    // information is supplied.
    // -----------------------------------------------

    final dynamic allowCredentialsValue =
        options['allowCredentials'];

    if (allowCredentialsValue is List) {
      final List<dynamic> allowCredentials =
          List<dynamic>.from(
        allowCredentialsValue,
      );

      final List<dynamic> normalizedCredentials =
          <dynamic>[];

      for (final dynamic credential
          in allowCredentials) {
        if (credential is Map) {
          final Map<String, dynamic> normalized =
              Map<String, dynamic>.from(
            credential,
          );

          if (normalized['transports'] == null) {
            normalized['transports'] =
                <String>[];
          }

          normalizedCredentials.add(
            normalized,
          );
        } else {
          normalizedCredentials.add(
            credential,
          );
        }
      }

      options['allowCredentials'] =
          normalizedCredentials;
    }

    // -----------------------------------------------
    // Convert the corrected options back to JSON.
    // -----------------------------------------------

    final String normalizedOptionsJson =
        jsonEncode(options);

    // -----------------------------------------------
    // Create authentication request.
    // -----------------------------------------------

    final AuthenticateRequestType request =
        AuthenticateRequestType.fromJsonString(
      normalizedOptionsJson,
      mediation: MediationType.Optional,
      preferImmediatelyAvailableCredentials: false,
    );

    // -----------------------------------------------
    // Ask Android Credential Manager to authenticate.
    // -----------------------------------------------

    final AuthenticateResponseType response =
        await authenticator.authenticate(
      request,
    );

    // -----------------------------------------------
    // Convert assertion response to JSON.
    // -----------------------------------------------

    return response.toJson();
  }
}