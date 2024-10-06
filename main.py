# Main Code
import json
import datetime
import mstarpy

def process_transactions(transaction_detail):
    portfolio = {}
    gain_details = {}
    transactions = transaction_detail['data'][0]['dtTransaction']

    for trxn in transactions:
        trxn['trxnDate'] = datetime.datetime.strptime(trxn['trxnDate'], '%d-%b-%Y')
    transactions = sorted(transactions, key=lambda x: x['trxnDate'])

    for trxn in transactions:
        isin = trxn['isin']
        folio = trxn['folio']
        fund_name = trxn['schemeName']
        units = float(trxn['trxnUnits'])
        price = float(trxn['purchasePrice'])

        if (folio, isin) not in portfolio:
            portfolio[(folio, isin)] = {"fund_name": fund_name, "transactions": []}

        if units > 0:
            portfolio[(folio, isin)]["transactions"].append([units, price, trxn['trxnDate']])
        else:
            # If units are negative (sell), we apply FIFO to remove purchased units
            remaining_units_to_sell = abs(units)
            while remaining_units_to_sell > 0:
                if not portfolio[(folio, isin)]["transactions"]:
                    print(f"Sell is more than Current Available for {folio} and #{isin}")
                    continue
                buy_units_qty, buy_price, buy_date = portfolio[(folio, isin)]["transactions"].pop(0)
                if buy_units_qty > remaining_units_to_sell:
                    portfolio[(folio, isin)]["transactions"].append([buy_units_qty - remaining_units_to_sell, buy_price, buy_date])
                    remaining_units_to_sell = 0
                else:
                    remaining_units_to_sell -= buy_units_qty

        # For Calculating gain
        if (folio, isin) not in gain_details:
            gain_details[(folio, isin)] = 0
        if units > 0:
            gain_details[(folio, isin)] += units * price

    return portfolio, gain_details

def calculate_portfolio_value(portfolio, gain_details):
    total_value = 0
    total_gain = 0
    fund_values = []

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=10)
    for (folio, isin), fund_data in portfolio.items():
        fund_name = fund_data["fund_name"]
        transactions = fund_data["transactions"]

        fund = mstarpy.Funds(term=isin, country="in")
        history = fund.nav(start_date=start_date, end_date=end_date, frequency="daily")
        current_nav = history[-1]['nav']
        remaining_units = sum([units for units, price, date in transactions])

        # current value
        current_value = remaining_units * current_nav

        # total value
        total_value += current_value

        gain_value = gain_details[(folio, isin)]
        gain = current_value - gain_value

        # total gain
        total_gain += gain

        fund_values.append({
            "folio": folio,
            "fund_name": fund_name,
            "remaining_units": remaining_units,
            "current_value": current_value,
            "gain": gain
        })

    return total_value, total_gain, fund_values

def main(transaction_data_file):
    with open(transaction_data_file, 'r') as file:
        transactions = json.load(file)

    # 1. FIFO Method to store the current transcations data
    portfolio, gain_details = process_transactions(transactions)

    # 2. Calculate total portfolio value and gains
    total_value, total_gain, fund_values = calculate_portfolio_value(portfolio, gain_details)

    print(f"Total Portfolio Value: {total_value} Rs")
    print(f"Total Portfolio Gain: {total_gain} Rs")

    for index, fund in enumerate(fund_values, start=1):
        print(f"Fund {index}:")
        print(f"  Folio            : {fund['folio']}")
        print(f"  Fund Name        : {fund['fund_name']}")
        print(f"  Remaining Units  : {fund['remaining_units']:.4f}")
        print(f"  Current Value    : {fund['current_value']:,.2f} Rs")
        print(f"  Gain             : {fund['gain']:,.2f} Rs")
        print("-" * 40)


if __name__ == "__main__":
    file_name = input()
    main(file_name)
