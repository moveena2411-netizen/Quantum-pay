import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('QuantumPay app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const QuantumPayApp());

    // Wait for the 2-second splash screen timer
    await tester.pump(const Duration(seconds: 2));

    // Allow the navigation to complete
    await tester.pump();

    expect(find.text('QuantumPay'), findsWidgets);
  });
}