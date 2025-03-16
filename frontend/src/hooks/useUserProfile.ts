import { useState, useEffect } from "react";
import { useAccount } from "wagmi";
import {
  fetchUserProfile,
  ProfileInfo,
  getDisplayName,
} from "../services/profileService";

/**
 * Custom hook to fetch and manage user profile information
 * @returns User profile information and utility functions
 */
export function useUserProfile() {
  const { address } = useAccount();
  const [profile, setProfile] = useState<ProfileInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!address) {
        setProfile(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const userProfile = await fetchUserProfile(address);
        setProfile(userProfile);
      } catch (err) {
        console.error("Error fetching user profile:", err);
        setError(
          err instanceof Error ? err : new Error("Failed to fetch profile")
        );
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, [address]);

  /**
   * Get the user's display name
   * @returns Formatted display name (ENS, profile name, or shortened address)
   */
  const getUserDisplayName = (): string => {
    return getDisplayName(address, profile);
  };

  return {
    profile,
    isLoading,
    error,
    getUserDisplayName,
  };
}
