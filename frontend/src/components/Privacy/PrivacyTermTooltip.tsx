/**
 * PrivacyTermTooltip - Reusable tooltip for explaining privacy concepts
 * Provides contextual education on hover/click without overwhelming users
 * Implements progressive disclosure principle (Tier 2.2)
 */

import React, { memo } from 'react';
import {
  Tooltip,
  TooltipProps,
  Icon,
  Link,
  HStack,
  Text,
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import { FaQuestionCircle, FaExternalLinkAlt } from 'react-icons/fa';
import { PRIVACY_CONCEPTS } from '../../constants/privacy';

interface PrivacyTermTooltipProps {
  term: keyof typeof PRIVACY_CONCEPTS;
  children: React.ReactNode;
  showIcon?: boolean;
}

export const PrivacyTermTooltip = memo(
  ({ term, children, showIcon = true }: PrivacyTermTooltipProps) => {
    const concept = PRIVACY_CONCEPTS[term] as any;
    const tooltipBg = useColorModeValue('gray.100', 'gray.700');
    const tooltipTextColor = useColorModeValue('gray.700', 'gray.100');
    const linkColor = useColorModeValue('blue.500', 'blue.300');

    if (!concept || !concept.title) return <>{children}</>;

    return (
      <Tooltip
        label={
          <Box p={2} maxW="250px">
            <Text fontSize="sm" fontWeight="semibold" mb={2}>
              {concept.title}
            </Text>
            <Text fontSize="xs" mb={2}>
              {concept.tooltip || concept.description}
            </Text>
            {concept.learnUrl && (
              <Link
                href={concept.learnUrl}
                isExternal
                fontSize="xs"
                color={linkColor}
                display="flex"
                alignItems="center"
                gap={1}
              >
                Learn more
                <Icon as={FaExternalLinkAlt} boxSize={2} />
              </Link>
            )}
          </Box>
        }
        bg={tooltipBg}
        color={tooltipTextColor}
        placement="top"
        hasArrow
      >
        <HStack spacing={1} display="inline-flex" cursor="help">
          {children}
          {showIcon && <Icon as={FaQuestionCircle} boxSize={3} color="blue.400" />}
        </HStack>
      </Tooltip>
    );
  }
);
PrivacyTermTooltip.displayName = 'PrivacyTermTooltip';
