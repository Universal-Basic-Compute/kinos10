# KinKong Liquidity Providing Strategy

This document details how KinKong provides liquidity to UBC/SOL and COMPUTE/SOL pools, enhancing ecosystem support while generating yield.

## Core Strategy

### Liquidity Allocation
- **Total Portfolio Allocation:** 30% of total portfolio
- **UBC/SOL Pool:** 15% of total portfolio (50% of LP budget)
- **COMPUTE/SOL Pool:** 15% of total portfolio (50% of LP budget)
- **Rebalance Frequency:** Weekly (every Friday)

> 💡 **Why 30% Allocation?**
> This allocation balances yield generation with trading capital needs, while limiting impermanent loss exposure to a manageable portion of the portfolio.

### Pool Selection Criteria

#### 1. Concentrated Liquidity Ranges
- **UBC/SOL:** ±20% from current price
- **COMPUTE/SOL:** ±15% from current price
- **Adjust ranges** based on 30-day volatility metrics

#### 2. Fee Tier Selection
- **UBC/SOL:** 2% fee tier
- **COMPUTE/SOL:** 2% fee tier
- **Review fee performance** monthly

> 📊 **Volatility-Based Ranges**
> Ranges are dynamically adjusted based on recent volatility, widening during high volatility periods and narrowing during stable periods to optimize fee capture.

## Position Management

### 🚀 Entry Strategy
- Staggered entry across 3 days to average price exposure
- Initial positions at 50% of target allocation
- Remaining 50% deployed after 7-day performance evaluation

### ⚖️ Rebalancing Rules
- Rebalance when price moves outside 50% of defined range
- Rebalance when impermanent loss exceeds 2% of position value
- Mandatory weekly evaluation (Fridays at 16:00 UTC)
- Emergency rebalance during extreme volatility (>30% daily move)

### 🚪 Exit Conditions
- Significant fundamental changes to either token
- Liquidity utilization falls below 30% for 7 consecutive days
- Better yield opportunities identified (>25% higher APR)
- Emergency protocol activation

## Risk Management

### Impermanent Loss Mitigation
- Total 30% of portfolio allocated to liquidity positions
- Equal 15% allocation to UBC/SOL and COMPUTE/SOL pools
- Hedging with 5% allocation to out-of-range options
- Weekly IL calculation and threshold monitoring
- Partial exit when IL exceeds 5% of position value

**Impermanent Loss Calculation:**
IL = 2 * sqrt(P_ratio) / (1 + P_ratio) - 1

Where:
- P_ratio = Current price / Entry price
- IL is expressed as a percentage loss

### Security Measures
- Smart contract audit verification before deployment
- Liquidity deployed only to official Orca/Raydium pools
- Multi-signature authorization for position adjustments
- Real-time monitoring of pool contract activity

## Performance Metrics

### Key Performance Indicators
- Total Fee APR (annualized)
- Impermanent Loss Percentage
- Net Yield (Fees - IL)
- Pool Utilization Rate

### Reporting Cadence
- Daily fee accrual monitoring
- Weekly performance review
- Monthly strategy optimization
- Quarterly risk assessment

## Implementation Process

### Technical Setup
1. Connect to Orca/Raydium concentrated liquidity pools via API
2. Implement automated monitoring for position status
3. Configure alerts for rebalancing triggers
4. Develop dashboard for real-time performance tracking

**API Integration:**
```
// Example API endpoint for position management
POST https://api.orca.so/v1/whirlpools/positions
{
  "tokenMintA": "UBC_MINT_ADDRESS",
  "tokenMintB": "SOL_MINT_ADDRESS",
  "tickLowerIndex": -20000,  // -20% from current price
  "tickUpperIndex": 20000,   // +20% from current price
  "liquidityAmount": "1000000000"
}
```

### Operational Workflow
1. **Analysis Phase (Thursday)**
   - Review market conditions
   - Calculate optimal ranges
   - Determine allocation adjustments

2. **Execution Phase (Friday)**
   - Close underperforming positions
   - Open new positions with updated ranges
   - Rebalance existing positions as needed

3. **Monitoring Phase (Continuous)**
   - Track fee generation hourly
   - Monitor price movements
   - Calculate impermanent loss
   - Check pool utilization metrics

## Expected Outcomes

### Target Metrics
- 💰 **Fee Generation:** 15-25% APR
- 📉 **Impermanent Loss:** <10% annually
- 📈 **Net Yield:** 10-15% APR
- 🔄 **Utilization Rate:** >70% average

### Strategic Benefits
- Enhanced token utility and ecosystem support
- Reduced slippage for KinKong trading operations
- Additional revenue stream independent of market direction
- Deeper market integration and protocol support

**Integration with Trading Strategy:**
Liquidity positions complement trading strategy by providing additional yield during sideways markets, reducing overall portfolio volatility, supporting ecosystem liquidity, and generating consistent fee income.

## Monitoring and Optimization

### Continuous Improvement
- Monthly review of range optimization strategies
- Testing of alternative liquidity deployment methods
- Comparison with single-sided staking returns
- Analysis of fee tier performance

### Risk Adjustments
- Reduce allocation during extreme market volatility
- Widen ranges during uncertain market conditions
- Implement dynamic fee tier selection based on volume
- Adjust position sizes based on historical IL metrics
