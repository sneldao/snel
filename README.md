# Brian API Integration for Scroll Swaps

This project implements the Brian API as an alternative solution for handling swaps on the Scroll network. The Brian API is an Intent Recognition and Execution Engine for Web3 interactions that can understand user intent, provide answers, build transactions, or generate smart contracts.

## Overview

The Scroll network has limited support for traditional aggregators like Uniswap v4 (not deployed) and KyberSwap (implementation issues). To address this, we've integrated the Brian API to provide a more reliable swap experience on Scroll.

## Features

- Automatic detection of Scroll network and use of Brian API for swaps
- Fallback to traditional aggregators if Brian API is unavailable
- Seamless integration with the existing swap UI
- Support for all token pairs available on Scroll

## Implementation Details

### Brian API Service

The `BrianAPIService` class in `app/services/brian_service.py` provides methods to interact with the Brian API:

- `get_swap_transaction`: Gets a swap transaction from the Brian API
- `extract_parameters`: Extracts parameters from a prompt
- `get_token_info`: Gets token information from the Brian API

### Scroll Handler

The `ScrollHandler` class in `app/services/scroll_handler.py` has been updated to use the Brian API for Scroll swaps:

- `use_brian_api`: Uses the Brian API to get a swap transaction for Scroll
- `get_recommended_aggregator`: Now recommends Brian API as the default aggregator for Scroll

### Swap Router

The swap router in `app/api/routes/swap_router.py` has been updated to handle Brian API swaps:

- Added Brian API as an option in the quotes list
- Updated the execute endpoint to handle Brian API swaps

### Frontend

The `AggregatorSelection` component has been updated to display the Brian API option for Scroll swaps:

- Added a special badge for the Brian API option
- Added a note about using Brian API for better Scroll swaps
- Auto-selects Brian API for Scroll swaps

## Configuration

To use the Brian API, you need to set the following environment variables:

```
BRIAN_API_KEY=your_brian_api_key_here
BRIAN_API_URL=https://api.brianknows.org/api/v0
```

You can get an API key from the [Brian API website](https://brianknows.org).

## Usage

When a user is on the Scroll network and initiates a swap, the system will automatically use the Brian API to get the best swap route. The user will see a "Recommended for Scroll" badge next to the Brian API option in the aggregator selection UI.

## Fallback Mechanism

If the Brian API is unavailable or returns an error, the system will fall back to the traditional aggregators with Scroll-specific fixes applied.
