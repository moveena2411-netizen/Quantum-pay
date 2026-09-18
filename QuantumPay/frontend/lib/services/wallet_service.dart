class Transaction {
  final String type;
  final String receiver;
  final double amount;
  final DateTime date;

  Transaction({
    required this.type,
    required this.receiver,
    required this.amount,
    required this.date,
  });
}

class WalletService {
  // ------------------------------------------------------------
  // LOCAL DEMO DATA
  // We will connect this to FastAPI/database in the next step.
  // ------------------------------------------------------------

  static double _balance = 25000.00;

  static final List<Transaction> _transactions = [
    Transaction(
      type: 'received',
      receiver: 'arun@gmail.com',
      amount: 1500.00,
      date: DateTime(2026, 9, 12, 16, 15),
    ),
    Transaction(
      type: 'sent',
      receiver: 'rahul@gmail.com',
      amount: 500.00,
      date: DateTime(2026, 9, 13, 10, 30),
    ),
  ];

  // ------------------------------------------------------------
  // INSTANCE GETTERS
  // ------------------------------------------------------------

  double get balance => _balance;

  List<Transaction> get transactions => _transactions;

  // ------------------------------------------------------------
  // SEND MONEY
  // ------------------------------------------------------------

  bool sendMoney({
    required String receiver,
    required double amount,
  }) {
    if (amount <= 0) {
      return false;
    }

    if (amount > _balance) {
      return false;
    }

    _balance -= amount;

    _transactions.insert(
      0,
      Transaction(
        type: 'sent',
        receiver: receiver,
        amount: amount,
        date: DateTime.now(),
      ),
    );

    return true;
  }

  // ------------------------------------------------------------
  // RECEIVE MONEY
  // ------------------------------------------------------------

  void receiveMoney({
    required String sender,
    required double amount,
  }) {
    if (amount <= 0) {
      return;
    }

    _balance += amount;

    _transactions.insert(
      0,
      Transaction(
        type: 'received',
        receiver: sender,
        amount: amount,
        date: DateTime.now(),
      ),
    );
  }
}