"use client";

import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useColorModeValue,
  Divider,
  List,
  ListItem,
  Link,
  Input,
  InputGroup,
  InputRightElement,
  useToast,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Flex,
  Icon,
  Center,
  Stack,
} from "@chakra-ui/react";
import {
  FaSearch,
  FaExternalLinkAlt,
  FaCheckCircle,
  FaShieldAlt,
  FaDollarSign,
  FaStar,
  FaRegStickyNote,
} from "react-icons/fa";

interface ProtocolResearchResultProps {
  content: any;
}

function stripCodeBlock(str: string): string {
  if (!str) return "";
  // Remove triple backtick code blocks (with or without 'json')
  return str.replace(/```(?:json)?\s*([\s\S]*?)\s*```/gi, "$1").trim();
}

function safeParseJson(json: any) {
  if (typeof json === "string") {
    const stripped = stripCodeBlock(json);
    try {
      return JSON.parse(stripped);
    } catch {
      return {};
    }
  }
  return json || {};
}

export const ProtocolResearchResult: React.FC<ProtocolResearchResultProps> = ({
  content,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [qaHistory, setQaHistory] = useState<
    Array<{ question: string; answer: string }>
  >([]);
  const toast = useToast();

  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");
  const textColor = useColorModeValue("gray.800", "white");
  const mutedColor = useColorModeValue("gray.600", "gray.400");
  const modalBgColor = useColorModeValue("gray.50", "gray.700");

  // Defensive: parse if backend ever returns a JSON string
  const parsed = safeParseJson(content);

  // Prefer AI fields, fallback to parsed
  const protocolName = parsed.protocol_name || parsed.name || "Protocol";
  const summary = parsed.ai_summary || parsed.summary || "No summary available";
  const protocolType = parsed.protocol_type || "DeFi Protocol";
  const keyFeatures = parsed.key_features || [];
  const securityInfo = parsed.security_info || "";
  const financialMetrics = parsed.financial_metrics || "";
  const analysisQuality = parsed.analysis_quality || "";
  const sourceUrl = parsed.source_url || "";
  const rawContent = parsed.raw_content || "";
  const hasAnalysis = !!summary && summary !== "No summary available";
  
  // Privacy-specific fields (from knowledge base)
  const privacyExplanation = parsed.privacy_explanation || "";
  const technicalExplanation = parsed.technical_explanation || "";
  const howItWorks = parsed.how_it_works || "";
  const recommendedWallets = parsed.recommended_wallets || [];
  const useCases = parsed.use_cases || [];
  const fromKnowledgeBase = parsed.from_knowledge_base || false;

  // Get protocol color scheme based on type
  const getProtocolColor = (type: string) => {
    if (type.includes("Lending")) return "blue";
    if (type.includes("Exchange")) return "green";
    if (type.includes("Staking")) return "purple";
    if (type.includes("Yield")) return "orange";
    return "gray";
  };
  const protocolColor = getProtocolColor(protocolType);

  const handleAskQuestion = async () => {
    if (!question.trim()) return;
    setIsAsking(true);
    try {
      // For knowledge-base results, synthesize content from available fields
      let contentToPass = rawContent;
      if (!contentToPass && summary) {
        // Create synthetic content from KB fields for knowledge base results
        contentToPass = [
          summary,
          keyFeatures.length > 0 ? `Key Features: ${keyFeatures.join(", ")}` : "",
          howItWorks ? `How It Works: ${howItWorks}` : "",
          privacyExplanation ? `Privacy: ${privacyExplanation}` : "",
          useCases.length > 0 ? `Use Cases: ${useCases.join(", ")}` : "",
        ]
          .filter(Boolean)
          .join("\n\n");
      }

      const response = await fetch("/api/v1/chat/ask-protocol-question", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protocol_name: protocolName,
          question: question.trim(),
          raw_content: contentToPass || "",
          openai_api_key: localStorage.getItem("openai_api_key") || "",
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      if (result.success) {
        setQaHistory((prev) => [
          ...prev,
          {
            question: question.trim(),
            answer: result.answer,
          },
        ]);
        setQuestion("");
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to get answer",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error("Ask question error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to ask question. Please try again.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
    setIsAsking(false);
  };

  if (!parsed || typeof parsed !== "object") {
    return <Text color="red.500">Invalid protocol research data received</Text>;
  }

  // Main Card UI
  return (
    <>
      <Box p={4} borderRadius="lg" borderWidth="1px" borderColor={borderColor} bg={bgColor}>
        <VStack spacing={4} align="stretch">
          {/* Header */}
           <HStack justify="space-between">
             <Text fontWeight="bold" fontSize="lg">{protocolName.toUpperCase()}</Text>
             <HStack>
               <Badge colorScheme={protocolColor}>{protocolType}</Badge>
               {analysisQuality && <Badge colorScheme="green">{analysisQuality}</Badge>}
               {fromKnowledgeBase && <Badge colorScheme="blue">Verified</Badge>}
             </HStack>
           </HStack>
          <Divider my={2} />



          {/* Key Features */}
          {keyFeatures.length > 0 && (
            <Box>
              <HStack mb={1}>
                <Icon as={FaStar} color={mutedColor} />
                <Text fontWeight="bold">Key Features</Text>
              </HStack>
              <List styleType="disc" pl={4}>
                {keyFeatures.map((feature: string, i: number) => (
                  <ListItem key={i}>{feature}</ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Security */}
          {securityInfo && (
            <Box>
              <HStack mb={1}>
                <Icon as={FaShieldAlt} color={mutedColor} />
                <Text fontWeight="bold">Security</Text>
              </HStack>
              <Text fontSize="sm">{securityInfo}</Text>
            </Box>
          )}

          {/* Financial Metrics */}
          {financialMetrics && (
            <Box>
              <HStack mb={1}>
                <Icon as={FaDollarSign} color={mutedColor} />
                <Text fontWeight="bold">Financial Metrics</Text>
              </HStack>
              <Text fontSize="sm">{financialMetrics}</Text>
            </Box>
          )}

          {/* Source Link and Actions - Centered and Stacked */}
          <Center mt={2}>
            <Stack direction="column" spacing={2} align="center" width="100%">
              {sourceUrl && (
                <Button
                  as={Link}
                  href={sourceUrl}
                  isExternal
                  colorScheme="blue"
                  variant="outline"
                  size="sm"
                  leftIcon={<FaExternalLinkAlt />}
                  width="100%"
                >
                  View Official Docs
                </Button>
              )}
              <Button
                size="sm"
                variant="solid"
                colorScheme={protocolColor}
                onClick={() => setIsModalOpen(true)}
                leftIcon={<FaSearch />}
                width="100%"
              >
                View Details
              </Button>
            </Stack>
          </Center>
        </VStack>
      </Box>

      {/* Detailed Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} size="xl">
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent
          borderRadius="xl"
          boxShadow="xl"
          bg={bgColor}
          border="1px solid"
          borderColor={borderColor}
          mx={4}
          maxW="800px"
        >
          <ModalHeader>
            <VStack spacing={2} align="stretch">
              <Flex align="center" gap={3}>
                <Icon as={FaSearch} color={`${protocolColor}.500`} boxSize={5} />
                <Text>{protocolName.toUpperCase()} Research</Text>
                <Badge colorScheme={protocolColor} variant="solid">
                  {protocolType}
                </Badge>
                {analysisQuality && <Badge colorScheme="green">{analysisQuality}</Badge>}
              </Flex>
            </VStack>
          </ModalHeader>
          <ModalCloseButton />

          <ModalBody pb={6} maxH="70vh" overflowY="auto">
            <VStack spacing={4} align="stretch">
              {/* Analysis in Progress or Analysis Complete Badge */}
              {!hasAnalysis || summary === "No summary available" ? (
                <Box p={4} bg={modalBgColor} borderRadius="md" textAlign="center">
                  <HStack justify="center" spacing={2} mb={2}>
                    <Icon as={FaSearch} color={mutedColor} />
                    <Text fontWeight="semibold" color={mutedColor}>
                      Analysis in Progress
                    </Text>
                  </HStack>
                  <Text fontSize="sm" color={mutedColor}>
                    We&apos;re gathering detailed information about {protocolName}. This may take a moment.
                  </Text>
                </Box>
              ) : null}

              {/* Accordion for Details */}
              <Accordion allowToggle>
                 {/* AI Analysis Summary - as first accordion item */}
                 {hasAnalysis && summary !== "No summary available" && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaCheckCircle} color="green.500" />
                           <Text fontWeight="semibold">AI Analysis Summary</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <Text fontSize="sm" color={textColor} lineHeight="1.6">
                         {summary}
                       </Text>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Key Features */}
                 {keyFeatures.length > 0 && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaStar} color={mutedColor} />
                           <Text fontWeight="semibold">Key Features</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <List spacing={2}>
                         {keyFeatures.map((feature: string, index: number) => (
                           <ListItem key={index}>{feature}</ListItem>
                         ))}
                       </List>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Privacy Explanation */}
                 {privacyExplanation && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaShieldAlt} color="purple.500" />
                           <Text fontWeight="semibold">Privacy Explanation</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <Text fontSize="sm" color={textColor} whiteSpace="pre-wrap" lineHeight="1.6">
                         {privacyExplanation}
                       </Text>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* How It Works */}
                 {howItWorks && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaShieldAlt} color="blue.500" />
                           <Text fontWeight="semibold">How It Works</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <Text fontSize="sm" color={textColor} whiteSpace="pre-wrap" lineHeight="1.6">
                         {howItWorks}
                       </Text>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Recommended Wallets */}
                 {recommendedWallets.length > 0 && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaCheckCircle} color="green.500" />
                           <Text fontWeight="semibold">Recommended Wallets</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <VStack spacing={2} align="stretch">
                         {recommendedWallets.map((wallet: any, index: number) => (
                           <Box key={index} p={2} bg={modalBgColor} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
                             <HStack justify="space-between" mb={1}>
                               <Text fontWeight="semibold" fontSize="sm">{wallet.name}</Text>
                               <Badge colorScheme="blue" fontSize="xs">{wallet.type}</Badge>
                             </HStack>
                             <Text fontSize="xs" color={mutedColor} mb={2}>{wallet.note}</Text>
                             {wallet.url && (
                               <Button
                                 as={Link}
                                 href={wallet.url}
                                 isExternal
                                 size="xs"
                                 variant="outline"
                                 colorScheme="blue"
                               >
                                 Visit Website
                               </Button>
                             )}
                           </Box>
                         ))}
                       </VStack>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Use Cases */}
                 {useCases.length > 0 && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaStar} color="orange.500" />
                           <Text fontWeight="semibold">Use Cases</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <List spacing={2}>
                         {useCases.map((useCase: string, index: number) => (
                           <ListItem key={index}>{useCase}</ListItem>
                         ))}
                       </List>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Security Information */}
                 {securityInfo && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaShieldAlt} color={mutedColor} />
                           <Text fontWeight="semibold">Security Information</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <Text fontSize="sm" color={textColor} whiteSpace="pre-wrap" lineHeight="1.6">
                         {securityInfo}
                       </Text>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
                 {/* Financial Metrics */}
                 {financialMetrics && (
                   <AccordionItem>
                     <AccordionButton>
                       <Box flex="1" textAlign="left">
                         <HStack>
                           <Icon as={FaDollarSign} color={mutedColor} />
                           <Text fontWeight="semibold">Financial Metrics</Text>
                         </HStack>
                       </Box>
                       <AccordionIcon />
                     </AccordionButton>
                     <AccordionPanel pb={4}>
                       <Text fontSize="sm" color={textColor} whiteSpace="pre-wrap" lineHeight="1.6">
                         {financialMetrics}
                       </Text>
                     </AccordionPanel>
                   </AccordionItem>
                 )}
               </Accordion>

              <Divider />

              {/* Q&A Section */}
              <Box>
                <Text fontWeight="semibold" mb={3}>
                  Ask a Question about {protocolName}
                </Text>
                {/* Q&A History */}
                {qaHistory.length > 0 && (
                  <VStack spacing={3} align="stretch" mb={4}>
                    {qaHistory.map((qa, index) => (
                      <Box key={index} p={3} bg={modalBgColor} borderRadius="md">
                        <Text fontSize="sm" fontWeight="medium" color={textColor} mb={1}>
                          Q: {qa.question}
                        </Text>
                        <Text fontSize="sm" color={mutedColor}>
                          A: {qa.answer}
                        </Text>
                      </Box>
                    ))}
                  </VStack>
                )}
                {/* Question Input */}
                <HStack spacing={2}>
                  <InputGroup>
                    <Input
                      placeholder={`Ask anything about ${protocolName}...`}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleAskQuestion()}
                      disabled={isAsking}
                      size="sm"
                    />
                    <InputRightElement width="4.5rem">
                      <Button
                        h="1.75rem"
                        size="sm"
                        onClick={handleAskQuestion}
                        isLoading={isAsking}
                        loadingText="..."
                        colorScheme={protocolColor}
                        disabled={!question.trim()}
                      >
                        Ask
                      </Button>
                    </InputRightElement>
                  </InputGroup>
                </HStack>
                <Text fontSize="xs" color={mutedColor} mt={2}>
                  Ask questions like &quot;What are the risks?&quot; or &quot;How does staking work?&quot;
                </Text>
              </Box>

              {/* Source Link - Centered and Stacked */}
              {sourceUrl && (
                <Center pt={2}>
                  <Button
                    as={Link}
                    href={sourceUrl}
                    isExternal
                    colorScheme="purple"
                    variant="outline"
                    size="sm"
                    leftIcon={<FaExternalLinkAlt />}
                  >
                    View Official Source
                  </Button>
                </Center>
              )}

              {/* Debug Information - Hidden by default */}
              {rawContent && (
                <Box mt={6}>
                  <Accordion allowToggle>
                    <AccordionItem border="none">
                      <AccordionButton px={0} py={2}>
                        <Box flex="1" textAlign="left">
                          <Text fontSize="xs" color={mutedColor} fontWeight="medium">
                            🔍 Debug: Raw Content
                          </Text>
                          <Text fontSize="xs" color={mutedColor} opacity={0.7}>
                            Technical data used for analysis
                          </Text>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel px={0} pb={4}>
                        <Box
                          p={3}
                          borderRadius="md"
                          bg={modalBgColor}
                          maxH="200px"
                          overflowY="auto"
                          border="1px solid"
                          borderColor={borderColor}
                          opacity={0.8}
                        >
                          <Text
                            fontSize="xs"
                            color={mutedColor}
                            whiteSpace="pre-wrap"
                            lineHeight="1.3"
                            fontFamily="mono"
                          >
                            {rawContent}
                          </Text>
                        </Box>
                      </AccordionPanel>
                    </AccordionItem>
                  </Accordion>
                </Box>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
