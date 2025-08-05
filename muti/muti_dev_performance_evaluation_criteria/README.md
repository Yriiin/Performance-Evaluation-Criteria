# WRC (Warranty Record Card) Management for Motorcycles

## Overview
This Odoo 14 module provides comprehensive WRC management functionality for motorcycle sales with automated service coupon generation and tracking.

## Key Features

### Auto-Save WRC Records
- Automatically creates WRC records when motorcycle sales are fully invoiced
- Auto-filled fields become read-only to prevent accidental changes
- Incomplete fields remain editable for manual completion

### Customer Profile (Auto-filled)
- Name, Address, Phone Number, Email, Birthday
- Data extracted from customer records

### Dealer Profile (Auto-filled) 
- Selling Dealer, Dealer Code, Dealer Address
- Data extracted from sale order or company information

### Unit Information
- **Model**: Extracted from product information
- **Engine No.**: Editable if not auto-populated
- **Frame No.**: Editable if not auto-populated
- **Date Purchased**: From sale order date
- **Color**: Extracted from product name
- **Brand**: Auto-extracted from product name prefixes:
  - HO = Honda
  - YA = Yamaha
  - KA = Kawasaki
  - SU = Suzuki
  - SK = Skygo
- **Payment Basis**: Cash/Installment
- **Quantity**: From order line
- **Classification**: Auto-classified as Commuter or BigBike based on model

### Motorcycle Classification System

#### Commuter Models:
- **Automatic**: Beat110, Dio110, Click125/150, ADV150, PCX160
- **CUB**: Wave110, XRM125, RS125/150, GTR150 Supra
- **Sports**: CRF150, XR150, CB150X, CRF250
- **Business**: TMX125 Alpha, TMX150 Supremo

#### BigBike Models:
- **Adventure**: CB500X, X-ADV750, CRF1100L, CRF1100 Adventure
- **Sports**: CB500F, CB650R, CB1000R
- **Super Sports**: CBR500R, CBR650R, CBR1000RR-R
- **Tourer**: CMX500 Rebel, GL1800 Goldwing

### Service Coupon System
Automatically generates 3 PMS-based service coupons per WRC record:

1. **Coupon 1**: 500–2,000 km or 3 months from purchase
2. **Coupon 2**: 2,001–6,000 km or 7 months from purchase  
3. **Coupon 3**: 6,001–12,000 km or 12 months from purchase

### Coupon Use Features
- **Use Coupon** button opens service form with:
  - Servicing Branch
  - FSC NO./Coupon Code Sequence (auto-filled)
  - FSC NO./Coupon Code
  - Actual Service Date
  - Accept Date (Date coupon received)
  - Mileage validation (must be within coupon's km range)
- **Automatic Validation**: Prevents use of overdue or out-of-range coupons
- **Status Tracking**: Active → Used → Expired progression

## Installation
1. Place module in Odoo addons directory
2. Update app list
3. Install "Performance Evaluation Criteria" module

## Usage
1. Create motorcycle sale orders as normal
2. When fully invoiced, WRC records are automatically created
3. View WRC records from Sale Order or WRC Management menu
4. Use service coupons when motorcycles come in for maintenance
5. Track service history and coupon usage

## Menu Structure
- **WRC Management**
  - **WRC Records**: View and manage all WRC records
  - **Service Coupons**: View and manage service coupons

## Technical Details
- Models: `wrc.record`, `service.coupon`, `service.coupon.use.wizard`
- Automatic field population based on sale order data
- PMS schedule calculations using relativedelta
- Daily cron job to mark overdue coupons as expired
- Integration with Sale Order workflow

## Support
For questions or issues, contact the development team.
