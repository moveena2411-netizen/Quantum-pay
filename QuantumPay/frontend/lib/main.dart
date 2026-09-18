import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'screens/welcome/welcome_screen.dart';

void main() {
  runApp(const QuantumPayApp());
}

class QuantumPayApp extends StatelessWidget {
  const QuantumPayApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'QuantumPay',
      theme: AppTheme.lightTheme,
      home: const WelcomeScreen(),
    );
  }
}