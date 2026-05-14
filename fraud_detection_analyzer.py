import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from collections import defaultdict

# Configuration
INPUT_FILE = 'fintech_data_cleaned.csv'
OUTPUT_FILE = 'fraud_detection_report.txt'
FRAUD_LOGS_FILE = 'fraud_alerts.json'
RISK_SCORES_FILE = 'customer_risk_scores.csv'

class FraudDetectionAnalyzer:
    def __init__(self, input_file):
        self.df = pd.read_csv(input_file)
        self.fraud_alerts = []
        self.risk_scores = {}
        self.analysis_results = {}
        
        # Calculate baseline metrics for anomaly detection
        self.amount_mean = self.df['amount'].mean()
        self.amount_std = self.df['amount'].std()
        self.amount_median = self.df['amount'].median()
        self.balance_mean = self.df['account_balance'].mean()
        
    def log_fraud_alert(self, customer_id, alert_type, severity, description, transaction_id=None):
        """Log a fraud alert"""
        self.fraud_alerts.append({
            'timestamp': datetime.now().isoformat(),
            'customer_id': str(customer_id),
            'transaction_id': str(transaction_id) if transaction_id else None,
            'alert_type': alert_type,
            'severity': severity,  # LOW, MEDIUM, HIGH, CRITICAL
            'description': description
        })
    
    def calculate_z_score(self, value, mean, std):
        """Calculate z-score for anomaly detection"""
        if std == 0:
            return 0
        return abs((value - mean) / std)
    
    def detect_amount_anomalies(self):
        """Detect transactions with unusual amounts (outliers)"""
        print("\n1. Detecting Amount Anomalies...")
        anomaly_count = 0
        
        for idx, row in self.df.iterrows():
            amount = row['amount']
            z_score = self.calculate_z_score(amount, self.amount_mean, self.amount_std)
            
            # Flag if amount is >3 standard deviations from mean (99.7% confidence)
            if z_score > 3:
                severity = 'CRITICAL' if z_score > 4 else 'HIGH'
                self.log_fraud_alert(
                    row['customer_id'],
                    'AMOUNT_ANOMALY',
                    severity,
                    f"Unusual transaction amount: ${amount:,.2f} (z-score: {z_score:.2f})",
                    row['transaction_id']
                )
                anomaly_count += 1
            elif z_score > 2:
                self.log_fraud_alert(
                    row['customer_id'],
                    'AMOUNT_ANOMALY',
                    'MEDIUM',
                    f"Moderately unusual amount: ${amount:,.2f} (z-score: {z_score:.2f})",
                    row['transaction_id']
                )
                anomaly_count += 1
        
        self.analysis_results['amount_anomalies'] = anomaly_count
        print(f"   ✓ Found {anomaly_count} transactions with anomalous amounts")
    
    def detect_rapid_transactions(self, time_window_minutes=5):
        """Detect multiple rapid transactions from same customer"""
        print("\n2. Detecting Rapid Sequential Transactions...")
        rapid_tx_count = 0
        
        # Convert timestamp to datetime (coerce invalid values to NaT)
        self.df['timestamp_dt'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
        
        # Use vectorized pandas operations for efficiency
        self.df['time_diff'] = self.df.groupby('customer_id')['timestamp_dt'].diff().dt.total_seconds() / 60
        
        # Find rapid transactions (within time window)
        rapid_mask = (self.df['time_diff'] > 0) & (self.df['time_diff'] < time_window_minutes)
        rapid_txs = self.df[rapid_mask]
        
        for idx, row in rapid_txs.iterrows():
            self.log_fraud_alert(
                row['customer_id'],
                'RAPID_TRANSACTIONS',
                'MEDIUM',
                f"Transaction {row['time_diff']:.1f} minutes after previous one",
                row['transaction_id']
            )
            rapid_tx_count += 1
        
        self.analysis_results['rapid_transactions'] = rapid_tx_count
        print(f"   ✓ Found {rapid_tx_count} instances of rapid sequential transactions")
    
    def detect_failed_retry_patterns(self, retry_window_hours=1):
        """Detect multiple failed attempts (potential brute force attempts)"""
        print("\n3. Detecting Failed Transaction Retries...")
        retry_count = 0
        
        # Get failed transactions only
        failed_txs = self.df[self.df['status'] == 'failed'].copy()
        failed_txs['timestamp_dt'] = pd.to_datetime(failed_txs['timestamp'], errors='coerce')
        failed_txs = failed_txs[failed_txs['timestamp_dt'].notna()]
        
        # Count failures per customer in time window
        for customer_id in failed_txs['customer_id'].unique():
            customer_failures = failed_txs[failed_txs['customer_id'] == customer_id].sort_values('timestamp_dt')
            
            if len(customer_failures) >= 2:
                # Check if multiple failures within retry window
                time_diffs = customer_failures['timestamp_dt'].diff().dt.total_seconds() / 3600
                if (time_diffs < retry_window_hours).any():
                    severity = 'CRITICAL' if len(customer_failures) > 3 else 'HIGH'
                    self.log_fraud_alert(
                        customer_id,
                        'FAILED_RETRIES',
                        severity,
                        f"{len(customer_failures)} failed transactions in {retry_window_hours} hours",
                        customer_failures.iloc[-1]['transaction_id']
                    )
                    retry_count += 1
        
        self.analysis_results['failed_retries'] = retry_count
        print(f"   ✓ Found {retry_count} customers with multiple failed attempts")
    
    def detect_geographic_impossibilities(self, max_speed_kmh=900):
        """Detect impossible location changes (same customer in different cities too quickly)"""
        print("\n4. Detecting Geographic Impossibilities...")
        geo_impossibilities = 0
        
        # Simplified: assume 50km between random cities (conservative estimate)
        assumed_distance_km = 50
        
        # Use vectorized operations
        self.df['location_changed'] = self.df.groupby('customer_id')['location'].shift() != self.df['location']
        self.df['time_diff_hours'] = self.df['time_diff'] * 60  # Convert minutes to hours
        
        # Check locations where they changed
        location_changes = self.df[self.df['location_changed'] & self.df['time_diff_hours'].notna()].copy()
        location_changes['required_speed'] = assumed_distance_km / location_changes['time_diff_hours']
        
        impossible = location_changes[location_changes['required_speed'] > max_speed_kmh]
        
        for idx, row in impossible.iterrows():
            self.log_fraud_alert(
                row['customer_id'],
                'GEOGRAPHIC_IMPOSSIBILITY',
                'HIGH',
                f"Impossible travel speed required: {row['required_speed']:.0f} km/h",
                row['transaction_id']
            )
            geo_impossibilities += 1
        
        self.analysis_results['geographic_impossibilities'] = geo_impossibilities
        print(f"   ✓ Found {geo_impossibilities} impossible location changes")
    
    def detect_unusual_merchant_amounts(self):
        """Detect amounts unusual for specific merchant categories"""
        print("\n5. Detecting Unusual Merchant Category Amounts...")
        unusual_merchant = 0
        
        # Calculate baseline amounts per merchant category
        category_stats = self.df.groupby('merchant_category')['amount'].agg(['mean', 'std', 'count'])
        
        for idx, row in self.df.iterrows():
            category = row['merchant_category']
            amount = row['amount']
            
            if category in category_stats.index and category_stats.loc[category, 'count'] > 10:
                cat_mean = category_stats.loc[category, 'mean']
                cat_std = category_stats.loc[category, 'std']
                
                z_score = self.calculate_z_score(amount, cat_mean, cat_std)
                
                # Flag if amount is unusual for this merchant category
                if z_score > 3:
                    self.log_fraud_alert(
                        row['customer_id'],
                        'UNUSUAL_MERCHANT_AMOUNT',
                        'HIGH',
                        f"Unusual {row['merchant_category']} purchase: ${amount:,.2f} (typical: ${cat_mean:,.2f})",
                        row['transaction_id']
                    )
                    unusual_merchant += 1
        
        self.analysis_results['unusual_merchant_amounts'] = unusual_merchant
        print(f"   ✓ Found {unusual_merchant} transactions with unusual amounts for merchant category")
    
    def detect_device_switching(self):
        """Detect unusual device switching patterns"""
        print("\n6. Detecting Suspicious Device Switching...")
        device_switches = 0
        
        for customer_id in self.df['customer_id'].unique():
            customer_txs = self.df[self.df['customer_id'] == customer_id].sort_values('timestamp_dt')
            # Filter out invalid timestamps
            customer_txs = customer_txs[customer_txs['timestamp_dt'].notna()]
            
            if len(customer_txs) < 3:
                continue
            
            device_changes = 0
            for i in range(len(customer_txs) - 1):
                if customer_txs.iloc[i]['device'] != customer_txs.iloc[i + 1]['device']:
                    device_changes += 1
            
            # Flag if customer switches devices frequently (more than 50% of transactions)
            if device_changes > len(customer_txs) * 0.5 and len(customer_txs) > 5:
                self.log_fraud_alert(
                    customer_id,
                    'DEVICE_SWITCHING',
                    'MEDIUM',
                    f"Frequent device switching: {device_changes} changes in {len(customer_txs)} transactions",
                    customer_txs.iloc[-1]['transaction_id']
                )
                device_switches += 1
        
        self.analysis_results['device_switches'] = device_switches
        print(f"   ✓ Found {device_switches} customers with suspicious device switching")
    
    def detect_balance_mismatches(self):
        """Detect transactions that don't match account balance"""
        print("\n7. Detecting Balance Mismatches...")
        balance_issues = 0
        
        for customer_id in self.df['customer_id'].unique():
            customer_txs = self.df[self.df['customer_id'] == customer_id].sort_values('timestamp_dt')
            
            if len(customer_txs) == 0:
                continue
            
            # Get the most recent transaction
            last_tx = customer_txs.iloc[-1]
            balance = last_tx['account_balance']
            tx_type = last_tx['transaction_type']
            amount = last_tx['amount']
            
            # Simple check: if it's a debit/withdrawal and balance seems too high
            if tx_type in ['debit', 'withdrawal'] and amount > balance:
                self.log_fraud_alert(
                    customer_id,
                    'BALANCE_MISMATCH',
                    'HIGH',
                    f"Transaction of ${amount:,.2f} exceeds balance of ${balance:,.2f}",
                    last_tx['transaction_id']
                )
                balance_issues += 1
        
        self.analysis_results['balance_mismatches'] = balance_issues
        print(f"   ✓ Found {balance_issues} potential balance mismatches")
    
    def calculate_customer_risk_scores(self):
        """Calculate fraud risk score for each customer (0-100)"""
        print("\n8. Calculating Customer Risk Scores...")
        
        for customer_id in self.df['customer_id'].unique():
            score = 0
            risk_factors = []
            
            customer_txs = self.df[self.df['customer_id'] == customer_id]
            customer_alerts = [a for a in self.fraud_alerts if a['customer_id'] == customer_id]
            
            # Factor 1: Number of fraud alerts (max 30 points)
            alert_count = len(customer_alerts)
            score += min(alert_count * 3, 30)
            if alert_count > 0:
                risk_factors.append(f"{alert_count} fraud alerts")
            
            # Factor 2: Failed transaction rate (max 20 points)
            failed_count = len(customer_txs[customer_txs['status'] == 'failed'])
            if len(customer_txs) > 0:
                failed_rate = failed_count / len(customer_txs)
                if failed_rate > 0.3:
                    score += 20
                    risk_factors.append(f"High failure rate: {failed_rate:.1%}")
                elif failed_rate > 0.1:
                    score += 10
            
            # Factor 3: Large transaction amounts (max 15 points)
            large_txs = len(customer_txs[customer_txs['amount'] > self.amount_mean * 3])
            if large_txs > 0:
                score += min(large_txs * 5, 15)
                risk_factors.append(f"{large_txs} very large transactions")
            
            # Factor 4: Location diversity (max 15 points)
            unique_locations = customer_txs['location'].nunique()
            if unique_locations > 5:
                score += 15
                risk_factors.append(f"Transactions in {unique_locations} different locations")
            
            # Factor 5: Account balance very low (max 10 points)
            min_balance = customer_txs['account_balance'].min()
            if min_balance < 100:
                score += 10
                risk_factors.append(f"Very low balance: ${min_balance:.2f}")
            
            # Factor 6: Reversed transactions (max 10 points)
            reversed_txs = len(customer_txs[customer_txs['status'] == 'reversed'])
            if reversed_txs > 0:
                score += reversed_txs * 2
                risk_factors.append(f"{reversed_txs} reversed transactions")
            
            # Cap score at 100
            score = min(score, 100)
            
            # Determine risk level
            if score >= 70:
                risk_level = 'CRITICAL'
            elif score >= 50:
                risk_level = 'HIGH'
            elif score >= 30:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            self.risk_scores[customer_id] = {
                'customer_id': customer_id,
                'risk_score': score,
                'risk_level': risk_level,
                'risk_factors': '; '.join(risk_factors) if risk_factors else 'No significant risk factors'
            }
        
        self.analysis_results['risk_scores_calculated'] = len(self.risk_scores)
        print(f"   ✓ Calculated risk scores for {len(self.risk_scores)} customers")
    
    def detect_concurrent_transactions(self, time_window_minutes=1):
        """Detect transactions that appear simultaneous (impossible)"""
        print("\n9. Detecting Concurrent Transactions...")
        concurrent_count = 0
        
        # Use vectorized operations
        self.df['time_diff'] = self.df.groupby('customer_id')['timestamp_dt'].diff().dt.total_seconds() / 60
        
        # Find concurrent transactions (same timestamp or within 1 minute)
        concurrent_mask = (self.df['time_diff'] > -1) & (self.df['time_diff'] < 1) & (self.df['time_diff'].notna())
        concurrent_txs = self.df[concurrent_mask & (self.df['timestamp_dt'].notna())]
        
        for idx, row in concurrent_txs.iterrows():
            self.log_fraud_alert(
                row['customer_id'],
                'CONCURRENT_TRANSACTIONS',
                'CRITICAL',
                f"Transaction {abs(row['time_diff']):.1f} minutes from previous one - impossible timing",
                row['transaction_id']
            )
            concurrent_count += 1
        
        self.analysis_results['concurrent_transactions'] = concurrent_count
        print(f"   ✓ Found {concurrent_count} concurrent transactions")
    
    def identify_high_risk_customers(self, threshold=50):
        """Identify customers with highest fraud risk"""
        print("\n10. Identifying High-Risk Customers...")
        
        high_risk = [cs for cs in self.risk_scores.values() if cs['risk_score'] >= threshold]
        high_risk_sorted = sorted(high_risk, key=lambda x: x['risk_score'], reverse=True)
        
        self.analysis_results['high_risk_customers'] = len(high_risk_sorted)
        self.analysis_results['high_risk_customer_list'] = high_risk_sorted[:20]  # Top 20
        
        print(f"   ✓ Identified {len(high_risk_sorted)} customers with risk score >= {threshold}")
    
    def analyze_all(self):
        """Execute full fraud detection analysis"""
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║         FINTECH FRAUD DETECTION ANALYSIS                     ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        
        self.detect_amount_anomalies()
        self.detect_rapid_transactions()
        self.detect_failed_retry_patterns()
        self.detect_geographic_impossibilities()
        self.detect_unusual_merchant_amounts()
        self.detect_device_switching()
        self.detect_balance_mismatches()
        self.calculate_customer_risk_scores()
        self.detect_concurrent_transactions()
        self.identify_high_risk_customers()
        
        print("\n✓ Fraud detection analysis completed")
    
    def generate_report(self):
        """Generate comprehensive fraud analysis report"""
        
        # Count alerts by severity
        severity_counts = defaultdict(int)
        for alert in self.fraud_alerts:
            severity_counts[alert['severity']] += 1
        
        # Count alerts by type
        alert_type_counts = defaultdict(int)
        for alert in self.fraud_alerts:
            alert_type_counts[alert['alert_type']] += 1
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   FINTECH FRAUD DETECTION REPORT                            ║
║                          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

EXECUTIVE SUMMARY
─────────────────────────────────────────────────────────────────────────────
Total Transactions Analyzed:    {len(self.df):,}
Total Unique Customers:         {self.df['customer_id'].nunique():,}
Total Fraud Alerts Generated:   {len(self.fraud_alerts):,}
Alerts per Transaction:         {len(self.fraud_alerts)/len(self.df):.2%}

ALERT SEVERITY BREAKDOWN
─────────────────────────────────────────────────────────────────────────────"""
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = severity_counts.get(severity, 0)
            percentage = (count / len(self.fraud_alerts) * 100) if self.fraud_alerts else 0
            report += f"\n{severity:12} {count:6,} alerts ({percentage:5.1f}%)"
        
        report += f"""

FRAUD DETECTION RESULTS
─────────────────────────────────────────────────────────────────────────────"""
        
        for alert_type, count in sorted(alert_type_counts.items(), key=lambda x: x[1], reverse=True):
            report += f"\n{alert_type:40} {count:6,} alerts"
        
        report += f"""

DETAILED FINDINGS
─────────────────────────────────────────────────────────────────────────────
1. Amount Anomalies
   - Transactions with unusual amounts: {self.analysis_results['amount_anomalies']:,}
   - These are >2 std dev from mean (>95% confidence)
   - Baseline mean: ${self.amount_mean:,.2f} | Median: ${self.amount_median:,.2f}

2. Rapid Sequential Transactions
   - Instances detected: {self.analysis_results['rapid_transactions']:,}
   - Time window analyzed: 5 minutes
   - Possible causes: Duplicate submissions, system errors, velocity testing

3. Failed Transaction Retries
   - Customers with multiple failures: {self.analysis_results['failed_retries']:,}
   - Possible causes: Invalid card, incorrect PIN, brute force attempts

4. Geographic Impossibilities
   - Impossible location changes: {self.analysis_results['geographic_impossibilities']:,}
   - Threshold: >900 km/h travel speed required
   - Risk: Account takeover/unauthorized access

5. Unusual Merchant Category Amounts
   - Transactions flagged: {self.analysis_results['unusual_merchant_amounts']:,}
   - Possible causes: Legitimate surge, testing, fraud

6. Suspicious Device Switching
   - Customers with unusual patterns: {self.analysis_results['device_switches']:,}
   - Risk: Account compromise, multiple users

7. Balance Mismatches
   - Potential fraudulent transactions: {self.analysis_results['balance_mismatches']:,}
   - Issue: Transaction exceeds account balance

8. Concurrent Transactions
   - Physically impossible transactions: {self.analysis_results['concurrent_transactions']:,}
   - Risk: System manipulation or account cloning

9. Customer Risk Scoring
   - Customers evaluated: {self.analysis_results['risk_scores_calculated']:,}
   - High-risk customers (score >= 50): {self.analysis_results['high_risk_customers']:,}

TOP 10 HIGH-RISK CUSTOMERS
─────────────────────────────────────────────────────────────────────────────
"""
        
        for i, customer in enumerate(self.analysis_results['high_risk_customer_list'][:10], 1):
            report += f"\n{i:2}. {customer['customer_id']} | Risk Score: {customer['risk_score']:3.0f}/100 ({customer['risk_level']})"
            report += f"\n    Factors: {customer['risk_factors'][:100]}..."
        
        report += f"""

RISK METRICS
─────────────────────────────────────────────────────────────────────────────
Transaction Success Rate:    {(len(self.df[self.df['status'] == 'completed']) / len(self.df) * 100):.1f}%
Failed Transaction Rate:     {(len(self.df[self.df['status'] == 'failed']) / len(self.df) * 100):.1f}%
Reversed Transaction Rate:   {(len(self.df[self.df['status'] == 'reversed']) / len(self.df) * 100):.1f}%
Average Transaction Amount:  ${self.amount_mean:,.2f}
High-Risk Customers (>50%):  {self.analysis_results['high_risk_customers']} of {self.df['customer_id'].nunique():,} ({self.analysis_results['high_risk_customers']/self.df['customer_id'].nunique()*100:.1f}%)

RECOMMENDATIONS
─────────────────────────────────────────────────────────────────────────────
1. IMMEDIATE ACTION (Risk Score > 75)
   - Block high-risk accounts for 24-48 hours pending verification
   - Contact customer to verify recent transactions
   - Review for potential compromise

2. ENHANCED MONITORING (Risk Score 50-75)
   - Require 2FA for next transaction
   - Monitor for escalation patterns
   - Geographic validation for large transactions

3. INVESTIGATION NEEDED
   - Examine failed retry patterns for brute force attacks
   - Analyze impossible geographic transitions
   - Review device switching patterns for account takeover

4. SYSTEM IMPROVEMENTS
   - Implement real-time geolocation validation
   - Add merchant category spending profiles
   - Enhanced concurrent transaction detection
   - Customer behavior baseline learning

OUTPUT FILES
─────────────────────────────────────────────────────────────────────────────
✓ Fraud Alerts:          {FRAUD_LOGS_FILE}
✓ Risk Scores:           {RISK_SCORES_FILE}
✓ Report:                {OUTPUT_FILE}

════════════════════════════════════════════════════════════════════════════════
"""
        
        return report
    
    def save_results(self):
        """Save all analysis results"""
        print("\nSaving results...")
        
        # Save fraud alerts
        with open(FRAUD_LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.fraud_alerts, f, indent=2)
        print(f"   ✓ Fraud alerts saved: {FRAUD_LOGS_FILE}")
        
        # Save risk scores
        risk_df = pd.DataFrame(self.risk_scores.values())
        risk_df = risk_df.sort_values('risk_score', ascending=False)
        risk_df.to_csv(RISK_SCORES_FILE, index=False)
        print(f"   ✓ Risk scores saved: {RISK_SCORES_FILE}")
        
        # Save report
        report = self.generate_report()
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"   ✓ Report saved: {OUTPUT_FILE}")
        
        return report

def main():
    try:
        analyzer = FraudDetectionAnalyzer(INPUT_FILE)
        analyzer.analyze_all()
        report = analyzer.save_results()
        print("\n" + report)
        print("\n✓ Fraud detection analysis completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
