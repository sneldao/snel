/**
 * Service for fetching user profile information from web3.bio API
 */

export interface ProfileInfo {
  address: string;
  identity: string;
  platform: string;
  displayName: string;
  avatar: string | null;
  description: string | null;
}

/**
 * Fetches a user's profile information from web3.bio API
 * @param address Ethereum address or ENS name
 * @returns Profile information or null if not found
 */
export async function fetchUserProfile(
  address: string
): Promise<ProfileInfo | null> {
  try {
    // Normalize the address
    const normalizedAddress = address.toLowerCase();

    // Call the web3.bio API
    const response = await fetch(
      `https://api.web3.bio/ns/${normalizedAddress}`
    );

    if (!response.ok) {
      console.error(
        `Error fetching profile: ${response.status} ${response.statusText}`
      );
      return null;
    }

    const data = await response.json();

    // If no profiles found
    if (!data || !Array.isArray(data) || data.length === 0) {
      return null;
    }

    // Find the best profile to use (prefer ENS, then Farcaster, then Lens)
    const ensProfile = data.find((p) => p.platform === "ens");
    const farcasterProfile = data.find((p) => p.platform === "farcaster");
    const lensProfile = data.find((p) => p.platform === "lens");

    // Use the first available profile in order of preference
    const profile = ensProfile || farcasterProfile || lensProfile || data[0];

    return {
      address: profile.address,
      identity: profile.identity,
      platform: profile.platform,
      displayName: profile.displayName || profile.identity,
      avatar: profile.avatar,
      description: profile.description,
    };
  } catch (error) {
    console.error("Error fetching user profile:", error);
    return null;
  }
}

/**
 * Gets a display name for a user based on their address
 * @param address Ethereum address
 * @returns Formatted display name (ENS or shortened address)
 */
export function getDisplayName(
  address: string | undefined,
  profile: ProfileInfo | null
): string {
  if (!address) return "User";

  // If we have a profile with a display name, use that
  if (profile?.displayName) {
    return profile.displayName;
  }

  // If the address is an ENS name (ends with .eth), use it directly
  if (address.endsWith(".eth")) {
    return address;
  }

  // Otherwise, shorten the address
  return shortenAddress(address);
}

/**
 * Shortens an Ethereum address for display
 * @param address Full Ethereum address
 * @returns Shortened address (e.g., 0x1234...5678)
 */
export function shortenAddress(address: string): string {
  if (!address) return "";
  if (address.length < 10) return address;

  return `${address.substring(0, 6)}...${address.substring(
    address.length - 4
  )}`;
}
