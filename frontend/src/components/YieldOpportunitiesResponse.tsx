import * as React from "react";
import {
    Box,
    Text,
    VStack,
    HStack,
    Badge,
    Button,
    Link,
    Divider,
    Icon,
    useColorModeValue,
} from "@chakra-ui/react";
import { FaLeaf, FaExternalLinkAlt, FaChartLine } from "react-icons/fa";

interface YieldOpportunity {
    protocol: string;
    apy: string;
    tvl?: string;
    chain: string;
    url?: string;
    description?: string;
}

interface YieldOpportunitiesResponseProps {
    content: {
        message: string;
        type: string;
        opportunities?: YieldOpportunity[];
    };
    onSetupYield?: (protocol: string, apy: string) => void;
}

export const YieldOpportunitiesResponse: React.FC<YieldOpportunitiesResponseProps> = ({
    content,
    onSetupYield,
}) => {
    const bg = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.600');

    const getAPYColor = (apy: string): string => {
        const apyValue = parseFloat(apy.replace('%', ''));
        if (apyValue >= 20) return 'green';
        if (apyValue >= 10) return 'blue';
        if (apyValue >= 5) return 'orange';
        return 'gray';
    };

    const handleSetupYield = (protocol: string, apy: string) => {
        if (onSetupYield) {
            onSetupYield(protocol, apy);
        } else {
            // Default behavior - suggest a command
            console.log(`Setup yield farming for ${protocol} with ${apy} APY`);
        }
    };

    if (content.type !== "yield_opportunities" || !content.opportunities) {
        return (
            <Box borderWidth="1px" borderRadius="lg" p={4} bg={bg}>
                <Text>{content.message}</Text>
            </Box>
        );
    }

    return (
        <Box borderWidth="1px" borderRadius="lg" p={4} bg={bg}>
            <HStack mb={4}>
                <Icon as={FaLeaf} color="green.500" />
                <Text fontWeight="bold">{content.message}</Text>
            </HStack>

            <VStack spacing={4} align="stretch">
                {content.opportunities.map((opportunity, index) => (
                    <Box
                        key={index}
                        p={4}
                        borderWidth="1px"
                        borderRadius="md"
                        borderColor={borderColor}
                        bg={bg}
                    >
                        <HStack justify="space-between" mb={2}>
                            <VStack align="start" spacing={1}>
                                <HStack>
                                    <Text fontWeight="bold">{opportunity.protocol}</Text>
                                    {opportunity.url && (
                                        <Link href={opportunity.url} isExternal>
                                            <FaExternalLinkAlt size={12} />
                                        </Link>
                                    )}
                                </HStack>
                                <HStack spacing={2}>
                                    <Badge colorScheme={getAPYColor(opportunity.apy)}>
                                        {opportunity.apy} APY
                                    </Badge>
                                    <Text fontSize="sm" color="gray.500">
                                        {opportunity.chain}
                                        {opportunity.tvl && (
                                            <>
                                                <Text fontSize="sm" color="gray.500">•</Text>
                                                <Text fontSize="sm" color="gray.500">
                                                    {opportunity.tvl} TVL
                                                </Text>
                                            </>
                                        )}
                                    </Text>
                                </HStack>
                            </VStack>
                            <Button
                                size="sm"
                                colorScheme="green"
                                variant="outline"
                                leftIcon={<FaChartLine />}
                                onClick={() => handleSetupYield(opportunity.protocol, opportunity.apy)}
                            >
                                Setup
                            </Button>
                        </HStack>
                        {opportunity.description && (
                            <Text fontSize="sm" color="gray.600" mt={2}>
                                {opportunity.description}
                            </Text>
                        )}
                    </Box>
                ))}

                <Divider />

                <Box textAlign="center" py={2}>
                    <Text fontSize="sm" color="gray.500">
                        💡 Try: "setup weekly 100 USDC for yield farming when APY &gt; 15%"
                    </Text>
                </Box>
            </VStack>
        </Box>
    );
};