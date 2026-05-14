import csv
import random
from datetime import datetime, timedelta
from faker import Faker
import string

fake = Faker()

# Configuration
NUM_RECORDS = 10000
ERROR_RATE = 0.15  # 15% of records will have errors
OUTPUT_FILE = 'fintech_sample_data.csv'

# Define transaction types and statuses
TRANSACTION_TYPES = ['debit', 'credit', 'transfer', 'withdrawal', 'deposit']
STATUSES = ['completed', 'pending', 'failed', 'reversed']
CURRENCIES = ['BRL', 'USD', 'EUR']

def generate_account_number():
    """Generate a realistic account number"""
    return f"{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"

def introduce_error(data):
    """Randomly introduce errors in the dataset"""
    error_type = random.choice([
        'invalid_email',
        'missing_phone',
        'negative_amount',
        'invalid_account',
        'duplicate_id',
        'invalid_date',
        'typo_name',
        'invalid_cpf',
        'amount_overflow',
        'empty_field'
    ])
    
    if error_type == 'invalid_email':
        data['email'] = fake.word() + '@invalid'
    elif error_type == 'missing_phone':
        data['phone'] = None
    elif error_type == 'negative_amount':
        if data['transaction_type'] == 'credit':
            data['amount'] = -abs(data['amount'])
    elif error_type == 'invalid_account':
        data['account_number'] = 'INVALID' + str(random.randint(1000, 9999))
    elif error_type == 'duplicate_id' and random.random() > 0.7:
        # Intentionally use a previous transaction ID
        data['transaction_id'] = str(random.randint(1, 100))
    elif error_type == 'invalid_date':
        data['timestamp'] = '2024-13-45 25:70:00'
    elif error_type == 'typo_name':
        name = data['customer_name']
        if len(name) > 2:
            name_list = list(name)
            idx = random.randint(0, len(name_list) - 1)
            name_list[idx] = random.choice(string.ascii_letters)
            data['customer_name'] = ''.join(name_list)
    elif error_type == 'invalid_cpf':
        data['cpf'] = 'XXX.XXX.XXX-XX'
    elif error_type == 'amount_overflow':
        data['amount'] = 999999999999.99
    elif error_type == 'empty_field':
        data['merchant_name'] = ''
    
    return data

def generate_cpf():
    """Generate a realistic Brazilian CPF"""
    return f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"

def generate_record(record_id):
    """Generate a single fintech data record"""
    has_error = random.random() < ERROR_RATE
    
    # Generate base data
    customer_name = fake.name()
    email = fake.email()
    phone = fake.phone_number()
    cpf = generate_cpf()
    account_number = generate_account_number()
    
    # Generate transaction data
    transaction_id = str(record_id).zfill(8)
    transaction_type = random.choice(TRANSACTION_TYPES)
    amount = round(random.uniform(10, 5000), 2)
    currency = random.choice(CURRENCIES)
    status = random.choice(STATUSES)
    
    # Generate timestamps
    days_ago = random.randint(0, 365)
    transaction_date = datetime.now() - timedelta(days=days_ago)
    timestamp = transaction_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Merchant/recipient info
    merchant_name = fake.company()
    merchant_category = random.choice(['Retail', 'Restaurant', 'Transport', 'Healthcare', 'Entertainment', 'Utilities', 'Gas Station'])
    
    # Account balance
    balance = round(random.uniform(100, 50000), 2)
    
    # Create record dictionary
    data = {
        'customer_id': f'CUST{record_id:08d}',
        'customer_name': customer_name,
        'email': email,
        'phone': phone,
        'cpf': cpf,
        'account_number': account_number,
        'account_balance': balance,
        'transaction_id': transaction_id,
        'transaction_type': transaction_type,
        'amount': amount,
        'currency': currency,
        'timestamp': timestamp,
        'merchant_name': merchant_name,
        'merchant_category': merchant_category,
        'status': status,
        'location': fake.city(),
        'device': random.choice(['Mobile', 'Web', 'ATM', 'Card']),
        'has_error': 'Yes' if has_error else 'No'
    }
    
    # Introduce errors if needed
    if has_error:
        data = introduce_error(data)
    
    return data

def main():
    """Generate and save fintech sample data"""
    print(f"Generating {NUM_RECORDS:,} sample FinTech datasets...")
    
    records = []
    for i in range(1, NUM_RECORDS + 1):
        record = generate_record(i)
        records.append(record)
        
        if i % 1000 == 0:
            print(f"  Generated {i:,} records...")
    
    # Write to CSV
    print(f"Writing data to {OUTPUT_FILE}...")
    
    fieldnames = [
        'customer_id', 'customer_name', 'email', 'phone', 'cpf',
        'account_number', 'account_balance', 'transaction_id',
        'transaction_type', 'amount', 'currency', 'timestamp',
        'merchant_name', 'merchant_category', 'status', 'location',
        'device', 'has_error'
    ]
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    # Print statistics
    error_count = sum(1 for r in records if r['has_error'] == 'Yes')
    print(f"\n✓ Successfully generated {NUM_RECORDS:,} records")
    print(f"✓ Records with errors: {error_count:,} ({error_count/NUM_RECORDS*100:.1f}%)")
    print(f"✓ File saved: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
