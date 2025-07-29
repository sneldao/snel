import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Flex,
  Text,
  HStack,
  VStack,
  IconButton,
  Tooltip,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  PopoverArrow,
  useColorModeValue,
  useColorMode,
  Badge,
  Kbd,
  Tag,
  TagLabel,
  TagLeftIcon,
  Collapse,
  Portal,
  Button,
  Divider,
  List,
  ListItem,
  useDisclosure,
  useToast,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SimpleGrid,
  Heading,
  Avatar,
  Icon,
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaMicrophone,
  FaMicrophoneSlash,
  FaHistory,
  FaLightbulb,
  FaEthereum,
  FaCoins,
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaChartPie,
  FaSearch,
  FaArrowUp,
  FaArrowDown,
  FaArrowRight,
  FaArrowLeft,
  FaGasPump,
  FaRocket,
  FaRegKeyboard,
  FaChevronDown,
  FaChevronUp,
  FaInfoCircle,
  FaRegLightbulb,
  FaMagic,
  FaPlus,
  FaMinus,
  FaCheck,
  FaTimes,
  FaEllipsisH,
  FaFilter,
  FaStar,
  FaRegStar,
} from "react-icons/fa";
import { useAccount, useBalance, useChainId } from "wagmi";
import { ethers } from "ethers";
import { debounce } from "lodash";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";

// Import our enhanced components
import EnhancedInput from "./ui/EnhancedInput";
import EnhancedButton from "./ui/EnhancedButton";
import EnhancedCard from "./ui/EnhancedCard";
import EnhancedLoader from "./ui/EnhancedLoader";
import EnhancedModal from "./ui/EnhancedModal";

// Import token and chain data
import { SUPPORTED_CHAINS } from "../constants/chains";
import { POPULAR_TOKENS } from "../constants/tokens";
import { COMMON_ADDRESSES } from "../constants/addresses";
import { COMMAND_TEMPLATES } from "../constants/commandTemplates";

// Import services
import { ApiService } from "../services/apiService";
import { PortfolioService } from "../services/portfolioService";
import { TokenService } from "../services/tokenService";

// Import utils
import { formatAddress, formatTokenAmount } from "../utils/formatters";
import { estimateGasCost } from "../utils/gasEstimator";
import { parseCommand } from "../utils/commandParser";
import { validateCommand } from "../utils/commandValidator";

// Animation variants
const suggestionVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 500,
    },
  },
  exit: { opacity: 0, y: 10, transition: { duration: 0.2 } },
};

const quickActionVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 500,
    },
  },
  hover: {
    scale: 1.05,
    transition: { duration: 0.2 },
  },
  tap: {
    scale: 0.95,
    transition: { duration: 0.1 },
  },
};

const pulseVariants = {
  idle: { scale: 1 },
  pulse: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      repeatType: "loop",
    },
  },
};

// Types and interfaces
interface EnhancedCommandInputProps {
  onSubmit: (command: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  initialValue?: string;
  showQuickActions?: boolean;
  showSuggestions?: boolean;
  showVoiceInput?: boolean;
  showCommandBuilder?: boolean;
  showGasEstimation?: boolean;
  portfolioData?: any;
  tokenBalances?: any[];
  recentCommands?: string[];
  maxHistoryItems?: number;
}

interface CommandSuggestion {
  command: string;
  description?: string;
  icon?: React.ReactNode;
  category?: string;
  isPopular?: boolean;
}

interface TokenSuggestion {
  symbol: string;
  name: string;
  address: string;
  chainId: number;
  logoURI?: string;
  balance?: string;
  price?: string;
}

interface AddressSuggestion {
  name: string;
  address: string;
  ens?: string;
  category?: string;
  icon?: React.ReactNode;
}

interface CommandBuilderStep {
  type: "action" | "token" | "amount" | "address" | "chain";
  value: string;
  options?: string[];
  placeholder?: string;
}

interface CommandTemplate {
  name: string;
  template: string;
  description: string;
  icon: React.ReactNode;
  category: string;
}

interface QuickAction {
  name: string;
  command: string;
  icon: React.ReactNode;
  color?: string;
}

// Main component
const EnhancedCommandInput: React.FC<EnhancedCommandInputProps> = ({
  onSubmit,
  isLoading = false,
  placeholder = "Type a command like 'swap 0.1 ETH for USDC'...",
  initialValue = "",
  showQuickActions = true,
  showSuggestions = true,
  showVoiceInput = true,
  showCommandBuilder = true,
  showGasEstimation = true,
  portfolioData,
  tokenBalances,
  recentCommands = [],
  maxHistoryItems = 10,
}) => {
  // Chakra hooks
  const toast = useToast();
  const { colorMode } = useColorMode();
  const {
    isOpen: isHistoryOpen,
    onToggle: toggleHistory,
    onClose: closeHistory,
  } = useDisclosure();
  const {
    isOpen: isCommandBuilderOpen,
    onToggle: toggleCommandBuilder,
    onClose: closeCommandBuilder,
  } = useDisclosure();

  // Theme colors
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const accentColor = useColorModeValue("blue.500", "blue.300");
  const subtleColor = useColorModeValue("gray.500", "gray.400");
  const hoverBgColor = useColorModeValue("gray.50", "gray.700");

  // Pre-compute color values for portfolio suggestion to avoid conditional hook calls
  const portfolioBgColor = useColorModeValue("blue.50", "blue.900");
  const portfolioBorderColor = useColorModeValue("blue.100", "blue.700");
  const portfolioTextColor = useColorModeValue("blue.700", "blue.200");

  // Pre-compute color values for command builder to avoid conditional hook calls
  const commandBuilderBgColor = useColorModeValue("gray.50", "gray.800");

  // Wallet hooks
  const { address, isConnected } = useAccount();
  const chainId = useChainId();

  // Voice recognition
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  // State
  const [commandValue, setCommandValue] = useState(initialValue);
  const [commandHistory, setCommandHistory] =
    useState<string[]>(recentCommands);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [suggestions, setSuggestions] = useState<CommandSuggestion[]>([]);
  const [tokenSuggestions, setTokenSuggestions] = useState<TokenSuggestion[]>(
    []
  );
  const [addressSuggestions, setAddressSuggestions] = useState<
    AddressSuggestion[]
  >([]);
  const [showSuggestionsList, setShowSuggestionsList] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    message?: string;
  }>({ isValid: true });
  const [gasEstimation, setGasEstimation] = useState<{
    cost: string;
    time: string;
  } | null>(null);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [favoriteCommands, setFavoriteCommands] = useState<string[]>(() => {
    const saved = localStorage.getItem("snel_favorite_commands");
    return saved ? JSON.parse(saved) : [];
  });
  const [commandBuilderSteps, setCommandBuilderSteps] = useState<
    CommandBuilderStep[]
  >([
    {
      type: "action",
      value: "",
      options: ["swap", "send", "bridge", "check", "analyze"],
    },
  ]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [magicSuggestion, setMagicSuggestion] = useState<string | null>(null);
  const [crossChainHint, setCrossChainHint] = useState<string | null>(null);
  const [portfolioSuggestion, setPortfolioSuggestion] = useState<string | null>(
    null
  );

  // Refs
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionRef = useRef<HTMLDivElement>(null);
  const previousCommandRef = useRef<string>("");

  // Services
  const apiService = React.useMemo(() => new ApiService(), []);
  const portfolioService = React.useMemo(
    () => new PortfolioService(apiService),
    [apiService]
  );
  const tokenService = React.useMemo(() => new TokenService(), []);

  // Quick actions
  const quickActions: QuickAction[] = [
    { name: "Swap", command: "swap ", icon: <FaExchangeAlt />, color: "blue" },
    { name: "Bridge", command: "bridge ", icon: <FaLink />, color: "purple" },
    { name: "Send", command: "send ", icon: <FaArrowRight />, color: "green" },
    {
      name: "Portfolio",
      command: "analyze my portfolio",
      icon: <FaChartPie />,
      color: "cyan",
    },
    {
      name: "Balance",
      command: "check my balance",
      icon: <FaWallet />,
      color: "yellow",
    },
    {
      name: "Research",
      command: "tell me about ",
      icon: <FaSearch />,
      color: "orange",
    },
  ];

  // Handle command submission
  const handleSubmit = () => {
    if (!commandValue.trim() || isLoading) return;

    // Add to history
    if (!commandHistory.includes(commandValue)) {
      const newHistory = [commandValue, ...commandHistory].slice(
        0,
        maxHistoryItems
      );
      setCommandHistory(newHistory);
      localStorage.setItem("snel_command_history", JSON.stringify(newHistory));
    }

    // Reset state
    previousCommandRef.current = commandValue;
    setHistoryIndex(-1);

    // Submit command
    onSubmit(commandValue);
    setCommandValue("");

    // Close any open panels
    setShowSuggestionsList(false);
    closeHistory();
    closeCommandBuilder();
  };

  // Handle key navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // History navigation
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setCommandValue(commandHistory[newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommandValue(commandHistory[newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCommandValue(previousCommandRef.current);
      }
    } else if (e.key === "Escape") {
      setShowSuggestionsList(false);
    } else if (e.key === "Tab" && suggestions.length > 0) {
      e.preventDefault();
      setCommandValue(suggestions[0].command);
    } else if (e.key === "Enter" && !isLoading) {
      handleSubmit();
    }
  };

  // Handle command change with debounce
  const debouncedAnalyzeCommand = useCallback(
    debounce((command: string) => {
      if (!command.trim()) {
        setSuggestions([]);
        setTokenSuggestions([]);
        setAddressSuggestions([]);
        setValidationResult({ isValid: true });
        setGasEstimation(null);
        setCrossChainHint(null);
        setShowSuggestionsList(false);
        return;
      }

      setIsAnalyzing(true);

      // Validate command
      const validation = validateCommand(command);
      setValidationResult(validation);

      // Generate suggestions
      generateSuggestions(command);

      // Check for tokens and addresses
      identifyTokensAndAddresses(command);

      // Estimate gas if applicable
      if (showGasEstimation) {
        estimateCommandGas(command);
      }

      // Check for cross-chain operations
      checkCrossChainOperation(command);

      // Generate portfolio-aware suggestions
      generatePortfolioSuggestions(command);

      setIsAnalyzing(false);
      setShowSuggestionsList(true);
    }, 300),
    [address, chainId, portfolioData]
  );

  // Handle command change
  const handleCommandChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setCommandValue(value);
    debouncedAnalyzeCommand(value);
  };

  // Generate command suggestions
  const generateSuggestions = (command: string) => {
    if (!command.trim()) {
      setSuggestions([]);
      return;
    }

    const lowerCommand = command.toLowerCase();
    const words = lowerCommand.split(" ");
    const lastWord = words[words.length - 1];

    let newSuggestions: CommandSuggestion[] = [];

    // Check for command templates
    const matchingTemplates = COMMAND_TEMPLATES.filter(
      (template) =>
        template.template.toLowerCase().includes(lowerCommand) ||
        template.name.toLowerCase().includes(lowerCommand)
    );

    newSuggestions = [
      ...newSuggestions,
      ...matchingTemplates.map((template) => ({
        command: template.template,
        description: template.description,
        icon: template.icon,
        category: template.category,
      })),
    ];

    // Add common command completions
    if (lowerCommand.startsWith("swap")) {
      if (!lowerCommand.includes("for")) {
        newSuggestions.push({
          command: `${command} for `,
          description: "Complete swap command",
          icon: <FaExchangeAlt />,
          category: "swap",
        });
      }
    }

    if (lowerCommand.startsWith("bridge")) {
      if (!lowerCommand.includes("from")) {
        newSuggestions.push({
          command: `${command} from `,
          description: "Specify source chain",
          icon: <FaLink />,
          category: "bridge",
        });
      } else if (!lowerCommand.includes("to")) {
        newSuggestions.push({
          command: `${command} to `,
          description: "Specify destination chain",
          icon: <FaLink />,
          category: "bridge",
        });
      }
    }

    if (lowerCommand.startsWith("send")) {
      if (!lowerCommand.includes("to")) {
        newSuggestions.push({
          command: `${command} to `,
          description: "Specify recipient",
          icon: <FaArrowRight />,
          category: "transfer",
        });
      }
    }

    // Add popular commands
    if (newSuggestions.length < 3) {
      const popularCommands = [
        {
          command: "swap 0.1 ETH for USDC",
          description: "Swap ETH for USDC",
          icon: <FaExchangeAlt />,
          category: "swap",
          isPopular: true,
        },
        {
          command: "analyze my portfolio",
          description: "View your portfolio breakdown",
          icon: <FaChartPie />,
          category: "portfolio",
          isPopular: true,
        },
        {
          command: "bridge 100 USDC from Ethereum to Polygon",
          description: "Bridge USDC to Polygon",
          icon: <FaLink />,
          category: "bridge",
          isPopular: true,
        },
      ];

      const filteredPopular = popularCommands.filter(
        (cmd) =>
          cmd.command.toLowerCase().includes(lowerCommand) &&
          !newSuggestions.some((s) => s.command === cmd.command)
      );

      newSuggestions = [...newSuggestions, ...filteredPopular];
    }

    // Add favorite commands
    const matchingFavorites = favoriteCommands
      .filter((cmd) => cmd.toLowerCase().includes(lowerCommand))
      .map((cmd) => ({
        command: cmd,
        description: "Favorite command",
        icon: <FaStar color="gold" />,
        category: "favorite",
      }));

    newSuggestions = [...matchingFavorites, ...newSuggestions];

    // Limit suggestions
    setSuggestions(newSuggestions.slice(0, 5));
  };

  // Identify tokens and addresses in command
  const identifyTokensAndAddresses = (command: string) => {
    const lowerCommand = command.toLowerCase();
    const words = lowerCommand.split(" ");

    // Check for token references
    const potentialTokens = words.filter(
      (word) =>
        word.startsWith("$") ||
        POPULAR_TOKENS.some((token) => token.symbol.toLowerCase() === word)
    );

    if (potentialTokens.length > 0) {
      const newTokenSuggestions = POPULAR_TOKENS.filter((token) =>
        potentialTokens.some((pt) =>
          token.symbol.toLowerCase().includes(pt.replace("$", "").toLowerCase())
        )
      ).map((token) => ({
        symbol: token.symbol,
        name: token.name,
        address: token.address,
        chainId: token.chainId,
        logoURI: token.logoURI,
      }));

      setTokenSuggestions(newTokenSuggestions.slice(0, 4));
    } else {
      setTokenSuggestions([]);
    }

    // Check for address references
    const potentialAddresses = words.filter(
      (word) =>
        word.endsWith(".eth") ||
        (word.startsWith("0x") && word.length >= 10) ||
        COMMON_ADDRESSES.some((addr) => addr.name.toLowerCase() === word)
    );

    if (potentialAddresses.length > 0) {
      const newAddressSuggestions = COMMON_ADDRESSES.filter((addr) =>
        potentialAddresses.some(
          (pa) =>
            addr.name.toLowerCase().includes(pa.toLowerCase()) ||
            addr.address.toLowerCase().includes(pa.toLowerCase()) ||
            (addr.ens && addr.ens.toLowerCase().includes(pa.toLowerCase()))
        )
      ).map((addr) => ({
        name: addr.name,
        address: addr.address,
        ens: addr.ens,
        category: addr.category,
        icon: addr.icon || <FaWallet />,
      }));

      setAddressSuggestions(newAddressSuggestions.slice(0, 4));
    } else {
      setAddressSuggestions([]);
    }
  };

  // Estimate gas for command
  const estimateCommandGas = async (command: string) => {
    if (!isConnected || !address || !chainId) {
      setGasEstimation(null);
      return;
    }

    const lowerCommand = command.toLowerCase();

    // Only estimate for transaction commands
    if (
      lowerCommand.startsWith("swap") ||
      lowerCommand.startsWith("send") ||
      lowerCommand.startsWith("bridge") ||
      lowerCommand.startsWith("transfer")
    ) {
      try {
        const parsedCommand = parseCommand(command);
        const estimation = await estimateGasCost(parsedCommand, chainId);
        setGasEstimation(estimation);
      } catch (error) {
        console.error("Error estimating gas:", error);
        setGasEstimation(null);
      }
    } else {
      setGasEstimation(null);
    }
  };

  // Check for cross-chain operations
  const checkCrossChainOperation = (command: string) => {
    const lowerCommand = command.toLowerCase();

    if (
      lowerCommand.includes("bridge") ||
      (lowerCommand.includes("from") &&
        lowerCommand.includes("to") &&
        Object.values(SUPPORTED_CHAINS).some((chain) =>
          lowerCommand.includes(chain.toLowerCase())
        ))
    ) {
      // Extract chains
      let sourceChain = "";
      let destChain = "";

      for (const [id, name] of Object.entries(SUPPORTED_CHAINS)) {
        if (lowerCommand.includes(`from ${name.toLowerCase()}`)) {
          sourceChain = name;
        }
        if (lowerCommand.includes(`to ${name.toLowerCase()}`)) {
          destChain = name;
        }
      }

      if (sourceChain && destChain) {
        setCrossChainHint(
          `Bridging from ${sourceChain} to ${destChain} uses Axelar Network`
        );
      } else {
        setCrossChainHint(
          "Cross-chain operations use Axelar Network for secure bridging"
        );
      }
    } else {
      setCrossChainHint(null);
    }
  };

  // Generate portfolio-aware suggestions
  const generatePortfolioSuggestions = (command: string) => {
    if (!portfolioData || !isConnected) {
      setPortfolioSuggestion(null);
      return;
    }

    const lowerCommand = command.toLowerCase();

    // If user is trying to swap a token they don't have enough of
    if (lowerCommand.startsWith("swap") && portfolioData.tokens) {
      const words = lowerCommand.split(" ");
      const amountIndex = words.findIndex((w) => !isNaN(parseFloat(w)));

      if (amountIndex > -1 && amountIndex + 1 < words.length) {
        const amount = parseFloat(words[amountIndex]);
        const tokenSymbol = words[amountIndex + 1]
          .toUpperCase()
          .replace("$", "");

        const token = portfolioData.tokens.find(
          (t: any) => t.symbol.toUpperCase() === tokenSymbol
        );

        if (token && parseFloat(token.balance) < amount) {
          setPortfolioSuggestion(
            `You only have ${token.balance} ${token.symbol} available. Try a smaller amount.`
          );
          return;
        }
      }
    }

    // Suggest diversification if portfolio is concentrated
    if (
      lowerCommand.includes("portfolio") &&
      portfolioData.tokens &&
      portfolioData.tokens.length > 0
    ) {
      const largestToken = [...portfolioData.tokens].sort(
        (a: any, b: any) => parseFloat(b.value) - parseFloat(a.value)
      )[0];

      if (
        largestToken &&
        parseFloat(largestToken.value) > portfolioData.totalValue * 0.7
      ) {
        setPortfolioSuggestion(
          `Your portfolio is heavily concentrated in ${
            largestToken.symbol
          } (${Math.round(
            (parseFloat(largestToken.value) / portfolioData.totalValue) * 100
          )}%). Consider diversifying.`
        );
        return;
      }
    }

    // Default suggestion based on portfolio composition
    if (
      portfolioData.tokens &&
      portfolioData.tokens.length > 0 &&
      !lowerCommand
    ) {
      const stablecoins = portfolioData.tokens.filter((t: any) =>
        ["USDC", "USDT", "DAI", "BUSD"].includes(t.symbol.toUpperCase())
      );

      const stablecoinValue = stablecoins.reduce(
        (acc: number, t: any) => acc + parseFloat(t.value),
        0
      );
      const stablecoinPercentage = stablecoinValue / portfolioData.totalValue;

      if (stablecoinPercentage < 0.1) {
        setPortfolioSuggestion(
          "Your portfolio has limited stablecoin exposure. Consider adding some for volatility protection."
        );
      } else {
        setPortfolioSuggestion(null);
      }
    } else {
      setPortfolioSuggestion(null);
    }
  };

  // Generate magic suggestion based on wallet state
  const generateMagicSuggestion = useCallback(() => {
    if (!isConnected || !address || !chainId || !tokenBalances) {
      setMagicSuggestion(null);
      return;
    }

    // Get current chain name
    const currentChain =
      SUPPORTED_CHAINS[chainId as keyof typeof SUPPORTED_CHAINS] || "Ethereum";

    // Find largest token balance
    const largestBalance = tokenBalances.sort(
      (a, b) => parseFloat(b.value || "0") - parseFloat(a.value || "0")
    )[0];

    // Generate suggestions based on wallet state
    if (largestBalance) {
      if (
        largestBalance.symbol === "ETH" ||
        largestBalance.symbol === "MATIC"
      ) {
        setMagicSuggestion(`swap 0.1 ${largestBalance.symbol} for USDC`);
      } else if (["USDC", "USDT", "DAI"].includes(largestBalance.symbol)) {
        // Suggest bridge if on Ethereum
        if (currentChain === "Ethereum") {
          setMagicSuggestion(
            `bridge 100 ${largestBalance.symbol} from Ethereum to Polygon`
          );
        } else {
          setMagicSuggestion(`swap 50 ${largestBalance.symbol} for ETH`);
        }
      } else {
        setMagicSuggestion(`analyze my portfolio`);
      }
    } else {
      setMagicSuggestion(`check my balance`);
    }
  }, [isConnected, address, chainId, tokenBalances]);

  // Toggle voice recognition
  const toggleVoiceRecognition = () => {
    if (!browserSupportsSpeechRecognition) {
      toast({
        title: "Voice Recognition Not Supported",
        description:
          "Your browser doesn't support voice recognition. Try Chrome or Edge.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (isVoiceListening) {
      SpeechRecognition.stopListening();
      setIsVoiceListening(false);

      // Set transcript as command value
      if (transcript) {
        setCommandValue(transcript);
        debouncedAnalyzeCommand(transcript);
        resetTranscript();
      }
    } else {
      SpeechRecognition.startListening({ continuous: true });
      setIsVoiceListening(true);
      toast({
        title: "Voice Recognition Active",
        description: "Speak your command clearly...",
        status: "info",
        duration: 2000,
        isClosable: true,
      });
    }
  };

  // Toggle favorite command
  const toggleFavoriteCommand = (command: string) => {
    const newFavorites = favoriteCommands.includes(command)
      ? favoriteCommands.filter((cmd) => cmd !== command)
      : [...favoriteCommands, command];

    setFavoriteCommands(newFavorites);
    localStorage.setItem(
      "snel_favorite_commands",
      JSON.stringify(newFavorites)
    );
  };

  // Update command builder
  const updateCommandBuilder = (stepIndex: number, value: string) => {
    const updatedSteps = [...commandBuilderSteps];
    updatedSteps[stepIndex].value = value;

    // Add next step if needed
    if (stepIndex === commandBuilderSteps.length - 1 && value) {
      let nextStep: CommandBuilderStep | null = null;

      switch (updatedSteps[stepIndex].type) {
        case "action":
          if (value === "swap") {
            nextStep = { type: "amount", value: "", placeholder: "Amount" };
          } else if (value === "send" || value === "bridge") {
            nextStep = { type: "amount", value: "", placeholder: "Amount" };
          } else if (value === "check") {
            nextStep = { type: "token", value: "", placeholder: "Token" };
          }
          break;
        case "amount":
          nextStep = { type: "token", value: "", placeholder: "Token" };
          break;
        case "token":
          if (updatedSteps[0].value === "swap") {
            nextStep = {
              type: "token",
              value: "",
              placeholder: "Target Token",
            };
          } else if (updatedSteps[0].value === "send") {
            nextStep = { type: "address", value: "", placeholder: "Recipient" };
          } else if (updatedSteps[0].value === "bridge") {
            nextStep = {
              type: "chain",
              value: "",
              placeholder: "Destination Chain",
            };
          }
          break;
      }

      if (nextStep) {
        updatedSteps.push(nextStep);
      }
    }

    setCommandBuilderSteps(updatedSteps);
    setCurrentStepIndex(stepIndex + 1);
  };

  // Build command from command builder
  const buildCommand = () => {
    let command = "";

    // Action
    if (commandBuilderSteps[0].value) {
      command += commandBuilderSteps[0].value;
    }

    // Amount and token
    if (commandBuilderSteps.length > 1 && commandBuilderSteps[1].value) {
      command += ` ${commandBuilderSteps[1].value}`;
    }

    if (commandBuilderSteps.length > 2 && commandBuilderSteps[2].value) {
      command += ` ${commandBuilderSteps[2].value}`;
    }

    // For swap commands
    if (
      commandBuilderSteps[0].value === "swap" &&
      commandBuilderSteps.length > 3 &&
      commandBuilderSteps[3].value
    ) {
      command += ` for ${commandBuilderSteps[3].value}`;
    }

    // For send commands
    if (
      commandBuilderSteps[0].value === "send" &&
      commandBuilderSteps.length > 3 &&
      commandBuilderSteps[3].value
    ) {
      command += ` to ${commandBuilderSteps[3].value}`;
    }

    // For bridge commands
    if (
      commandBuilderSteps[0].value === "bridge" &&
      commandBuilderSteps.length > 3 &&
      commandBuilderSteps[3].value
    ) {
      command += ` to ${commandBuilderSteps[3].value}`;
    }

    setCommandValue(command);
    closeCommandBuilder();
    inputRef.current?.focus();
  };

  // Load command history from localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem("snel_command_history");
    if (savedHistory) {
      setCommandHistory(JSON.parse(savedHistory));
    }
  }, []);

  // Update command value when transcript changes
  useEffect(() => {
    if (isVoiceListening && transcript) {
      setCommandValue(transcript);
      debouncedAnalyzeCommand(transcript);
    }
  }, [transcript, isVoiceListening]);

  // Generate magic suggestion on mount and when wallet state changes
  useEffect(() => {
    generateMagicSuggestion();
  }, [generateMagicSuggestion]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionRef.current &&
        !suggestionRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setShowSuggestionsList(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <Box position="relative" width="100%">
      {/* Main input */}
      <EnhancedInput
        name="command"
        inputType="text"
        placeholder={placeholder}
        value={commandValue}
        onChange={handleCommandChange}
        onKeyDown={handleKeyDown}
        ref={inputRef}
        size="lg"
        variant="floating"
        animate={true}
        animateLabel={true}
        isFullWidth={true}
        validationState={validationResult.isValid ? "none" : "warning"}
        errorText={validationResult.message}
        leftIcon={
          <Box color={subtleColor}>
            <FaSearch />
          </Box>
        }
        rightIcon={
          <HStack spacing={2}>
            {isAnalyzing && (
              <EnhancedLoader
                variant="spinner"
                size="xs"
                color={accentColor}
                speed="fast"
              />
            )}

            {showVoiceInput && browserSupportsSpeechRecognition && (
              <IconButton
                aria-label={
                  isVoiceListening ? "Stop voice input" : "Start voice input"
                }
                icon={
                  isVoiceListening ? <FaMicrophoneSlash /> : <FaMicrophone />
                }
                size="sm"
                variant="ghost"
                colorScheme={isVoiceListening ? "red" : "gray"}
                onClick={toggleVoiceRecognition}
              />
            )}

            <IconButton
              aria-label="Command history"
              icon={<FaHistory />}
              size="sm"
              variant="ghost"
              onClick={toggleHistory}
            />

            {showCommandBuilder && (
              <IconButton
                aria-label="Visual command builder"
                icon={<FaRegKeyboard />}
                size="sm"
                variant="ghost"
                onClick={toggleCommandBuilder}
              />
            )}
          </HStack>
        }
      />

      {/* Command suggestions */}
      <AnimatePresence>
        {showSuggestions &&
          showSuggestionsList &&
          (suggestions.length > 0 ||
            tokenSuggestions.length > 0 ||
            addressSuggestions.length > 0) && (
            <motion.div
              ref={suggestionRef}
              variants={suggestionVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <Box
                position="absolute"
                top="100%"
                left={0}
                right={0}
                mt={2}
                zIndex={10}
                bg={bgColor}
                borderRadius="md"
                boxShadow="lg"
                border="1px solid"
                borderColor={borderColor}
                overflow="hidden"
              >
                {/* Command suggestions */}
                {suggestions.length > 0 && (
                  <Box p={2}>
                    <Text
                      fontSize="xs"
                      fontWeight="medium"
                      color={subtleColor}
                      mb={2}
                    >
                      SUGGESTIONS
                    </Text>
                    <VStack align="stretch" spacing={1}>
                      {suggestions.map((suggestion, index) => (
                        <Flex
                          key={index}
                          p={2}
                          borderRadius="md"
                          align="center"
                          justify="space-between"
                          cursor="pointer"
                          _hover={{ bg: hoverBgColor }}
                          onClick={() => {
                            setCommandValue(suggestion.command);
                            setShowSuggestionsList(false);
                            inputRef.current?.focus();
                          }}
                        >
                          <HStack>
                            {suggestion.icon && (
                              <Box color={accentColor} fontSize="sm">
                                {suggestion.icon}
                              </Box>
                            )}
                            <Text fontWeight="medium">
                              {suggestion.command}
                            </Text>
                          </HStack>
                          <HStack>
                            {suggestion.description && (
                              <Text fontSize="xs" color={subtleColor}>
                                {suggestion.description}
                              </Text>
                            )}
                            <IconButton
                              aria-label={
                                favoriteCommands.includes(suggestion.command)
                                  ? "Remove from favorites"
                                  : "Add to favorites"
                              }
                              icon={
                                favoriteCommands.includes(
                                  suggestion.command
                                ) ? (
                                  <FaStar />
                                ) : (
                                  <FaRegStar />
                                )
                              }
                              size="xs"
                              variant="ghost"
                              color={
                                favoriteCommands.includes(suggestion.command)
                                  ? "yellow.500"
                                  : subtleColor
                              }
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleFavoriteCommand(suggestion.command);
                              }}
                            />
                          </HStack>
                        </Flex>
                      ))}
                    </VStack>
                  </Box>
                )}

                {/* Token suggestions */}
                {tokenSuggestions.length > 0 && (
                  <Box
                    p={2}
                    borderTopWidth={suggestions.length > 0 ? "1px" : 0}
                    borderColor={borderColor}
                  >
                    <Text
                      fontSize="xs"
                      fontWeight="medium"
                      color={subtleColor}
                      mb={2}
                    >
                      TOKENS
                    </Text>
                    <SimpleGrid columns={2} spacing={2}>
                      {tokenSuggestions.map((token, index) => (
                        <Flex
                          key={index}
                          p={2}
                          borderRadius="md"
                          align="center"
                          cursor="pointer"
                          _hover={{ bg: hoverBgColor }}
                          onClick={() => {
                            // Replace token reference in command
                            const words = commandValue.split(" ");
                            const tokenIndex = words.findIndex(
                              (word) =>
                                word.startsWith("$") ||
                                word.toLowerCase() ===
                                  token.symbol.toLowerCase()
                            );

                            if (tokenIndex >= 0) {
                              words[tokenIndex] = token.symbol;
                              setCommandValue(words.join(" "));
                            } else {
                              setCommandValue(
                                commandValue + " " + token.symbol
                              );
                            }

                            setShowSuggestionsList(false);
                            inputRef.current?.focus();
                          }}
                        >
                          <Avatar
                            size="xs"
                            src={token.logoURI}
                            name={token.symbol}
                            mr={2}
                          />
                          <Box>
                            <Text fontWeight="medium" fontSize="sm">
                              {token.symbol}
                            </Text>
                            <Text fontSize="xs" color={subtleColor}>
                              {token.name}
                            </Text>
                          </Box>
                        </Flex>
                      ))}
                    </SimpleGrid>
                  </Box>
                )}

                {/* Address suggestions */}
                {addressSuggestions.length > 0 && (
                  <Box
                    p={2}
                    borderTopWidth={
                      suggestions.length > 0 || tokenSuggestions.length > 0
                        ? "1px"
                        : 0
                    }
                    borderColor={borderColor}
                  >
                    <Text
                      fontSize="xs"
                      fontWeight="medium"
                      color={subtleColor}
                      mb={2}
                    >
                      ADDRESSES
                    </Text>
                    <VStack align="stretch" spacing={1}>
                      {addressSuggestions.map((address, index) => (
                        <Flex
                          key={index}
                          p={2}
                          borderRadius="md"
                          align="center"
                          justify="space-between"
                          cursor="pointer"
                          _hover={{ bg: hoverBgColor }}
                          onClick={() => {
                            // Replace address reference in command
                            const words = commandValue.split(" ");
                            const addressIndex = words.findIndex(
                              (word) =>
                                word.endsWith(".eth") ||
                                (word.startsWith("0x") && word.length >= 10) ||
                                word.toLowerCase() ===
                                  address.name.toLowerCase()
                            );

                            if (addressIndex >= 0) {
                              words[addressIndex] = address.ens || address.name;
                              setCommandValue(words.join(" "));
                            } else {
                              setCommandValue(
                                commandValue +
                                  " " +
                                  (address.ens || address.name)
                              );
                            }

                            setShowSuggestionsList(false);
                            inputRef.current?.focus();
                          }}
                        >
                          <HStack>
                            <Box color={accentColor} fontSize="sm">
                              {address.icon}
                            </Box>
                            <Box>
                              <Text fontWeight="medium">{address.name}</Text>
                              <Text fontSize="xs" color={subtleColor}>
                                {address.ens || formatAddress(address.address)}
                              </Text>
                            </Box>
                          </HStack>
                          {address.category && (
                            <Badge
                              colorScheme="blue"
                              variant="subtle"
                              fontSize="xs"
                            >
                              {address.category}
                            </Badge>
                          )}
                        </Flex>
                      ))}
                    </VStack>
                  </Box>
                )}
              </Box>
            </motion.div>
          )}
      </AnimatePresence>

      {/* Gas estimation */}
      <AnimatePresence>
        {showGasEstimation && gasEstimation && (
          <motion.div
            variants={suggestionVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <Flex
              mt={2}
              p={2}
              borderRadius="md"
              bg={bgColor}
              borderWidth="1px"
              borderColor={borderColor}
              align="center"
              justify="space-between"
            >
              <HStack>
                <Icon as={FaGasPump} color={accentColor} />
                <Text fontSize="sm">Estimated Gas:</Text>
                <Text fontSize="sm" fontWeight="medium">
                  {gasEstimation.cost}
                </Text>
              </HStack>
              <HStack>
                <Icon as={FaRocket} color={accentColor} />
                <Text fontSize="sm">Est. Time:</Text>
                <Text fontSize="sm" fontWeight="medium">
                  {gasEstimation.time}
                </Text>
              </HStack>
            </Flex>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Cross-chain hint */}
      <AnimatePresence>
        {crossChainHint && (
          <motion.div
            variants={suggestionVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <Flex
              mt={2}
              p={2}
              borderRadius="md"
              bg={bgColor}
              borderWidth="1px"
              borderColor={borderColor}
              align="center"
            >
              <Icon as={FaLink} color="purple.500" mr={2} />
              <Text fontSize="sm">{crossChainHint}</Text>
            </Flex>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Portfolio suggestion */}
      <AnimatePresence>
        {portfolioSuggestion && (
          <motion.div
            variants={suggestionVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <Flex
              mt={2}
              p={2}
              borderRadius="md"
              bg={portfolioBgColor}
              borderWidth="1px"
              borderColor={portfolioBorderColor}
              align="center"
            >
              <Icon as={FaChartPie} color="blue.500" mr={2} />
              <Text fontSize="sm" color={portfolioTextColor}>
                {portfolioSuggestion}
              </Text>
            </Flex>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Magic suggestion */}
      <AnimatePresence>
        {magicSuggestion && (
          <motion.div variants={pulseVariants} initial="idle" animate="pulse">
            <Flex mt={3} justify="center">
              <EnhancedButton
                variant="ghost"
                size="sm"
                leftIcon={<FaMagic />}
                onClick={() => {
                  setCommandValue(magicSuggestion);
                  setShowSuggestionsList(false);
                  inputRef.current?.focus();
                  setTimeout(() => {
                    handleSubmit();
                  }, 500);
                }}
                animate={true}
                pulseEffect={true}
              >
                Try: {magicSuggestion}
              </EnhancedButton>
            </Flex>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick actions */}
      {showQuickActions && (
        <Box mt={4}>
          <HStack spacing={2} justify="center" wrap="wrap">
            {quickActions.map((action, index) => (
              <motion.div
                key={index}
                variants={quickActionVariants}
                initial="hidden"
                animate="visible"
                whileHover="hover"
                whileTap="tap"
                custom={index}
              >
                <EnhancedButton
                  variant="outline"
                  size="sm"
                  leftIcon={action.icon}
                  colorScheme={action.color}
                  onClick={() => {
                    setCommandValue(action.command);
                    inputRef.current?.focus();
                  }}
                >
                  {action.name}
                </EnhancedButton>
              </motion.div>
            ))}
          </HStack>
        </Box>
      )}

      {/* Command history drawer */}
      <Drawer
        isOpen={isHistoryOpen}
        placement="bottom"
        onClose={closeHistory}
        finalFocusRef={inputRef}
      >
        <DrawerOverlay backdropFilter="blur(4px)" />
        <DrawerContent borderTopRadius="lg" maxH="50vh">
          <DrawerHeader borderBottomWidth="1px">
            <Flex justify="space-between" align="center">
              <HStack>
                <FaHistory />
                <Text>Command History</Text>
              </HStack>
              <DrawerCloseButton position="static" />
            </Flex>
          </DrawerHeader>
          <DrawerBody>
            {commandHistory.length > 0 ? (
              <VStack align="stretch" spacing={1}>
                {commandHistory.map((cmd, index) => (
                  <Flex
                    key={index}
                    p={2}
                    borderRadius="md"
                    align="center"
                    justify="space-between"
                    cursor="pointer"
                    _hover={{ bg: hoverBgColor }}
                    onClick={() => {
                      setCommandValue(cmd);
                      closeHistory();
                      inputRef.current?.focus();
                    }}
                  >
                    <Text>{cmd}</Text>
                    <HStack>
                      <IconButton
                        aria-label={
                          favoriteCommands.includes(cmd)
                            ? "Remove from favorites"
                            : "Add to favorites"
                        }
                        icon={
                          favoriteCommands.includes(cmd) ? (
                            <FaStar />
                          ) : (
                            <FaRegStar />
                          )
                        }
                        size="xs"
                        variant="ghost"
                        color={
                          favoriteCommands.includes(cmd)
                            ? "yellow.500"
                            : subtleColor
                        }
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFavoriteCommand(cmd);
                        }}
                      />
                      <IconButton
                        aria-label="Use command"
                        icon={<FaArrowUp />}
                        size="xs"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCommandValue(cmd);
                          closeHistory();
                          handleSubmit();
                        }}
                      />
                    </HStack>
                  </Flex>
                ))}
              </VStack>
            ) : (
              <Flex direction="column" align="center" justify="center" h="100%">
                <Text color={subtleColor}>No command history yet</Text>
              </Flex>
            )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Command builder modal */}
      <EnhancedModal
        isOpen={isCommandBuilderOpen}
        onClose={closeCommandBuilder}
        title="Visual Command Builder"
        variant="centered"
        animation="scale"
        size="lg"
        primaryAction={{
          label: "Build Command",
          onClick: buildCommand,
          icon: <FaCheck />,
        }}
        secondaryAction={{
          label: "Cancel",
          onClick: closeCommandBuilder,
          icon: <FaTimes />,
        }}
        headerIcon={<FaRegKeyboard />}
      >
        <VStack spacing={6} align="stretch">
          <Box>
            <Text mb={4}>Build your command step by step:</Text>

            <VStack spacing={4} align="stretch">
              {commandBuilderSteps.map((step, index) => (
                <Box key={index}>
                  <Text fontSize="sm" fontWeight="medium" mb={2}>
                    {index === 0
                      ? "Action:"
                      : step.type === "amount"
                      ? "Amount:"
                      : step.type === "token"
                      ? index === 2
                        ? "Token:"
                        : "Target Token:"
                      : step.type === "address"
                      ? "Recipient:"
                      : step.type === "chain"
                      ? "Destination Chain:"
                      : "Value:"}
                  </Text>

                  {step.type === "action" && (
                    <SimpleGrid columns={3} spacing={3}>
                      {["swap", "send", "bridge", "check", "analyze"].map(
                        (action) => (
                          <EnhancedButton
                            key={action}
                            variant={
                              step.value === action ? "solid" : "outline"
                            }
                            colorScheme={
                              step.value === action ? "blue" : "gray"
                            }
                            size="md"
                            onClick={() => updateCommandBuilder(index, action)}
                          >
                            {action.charAt(0).toUpperCase() + action.slice(1)}
                          </EnhancedButton>
                        )
                      )}
                    </SimpleGrid>
                  )}

                  {step.type === "amount" && (
                    <HStack spacing={3}>
                      {["0.1", "1", "10", "100"].map((amount) => (
                        <EnhancedButton
                          key={amount}
                          variant={step.value === amount ? "solid" : "outline"}
                          colorScheme={step.value === amount ? "blue" : "gray"}
                          size="md"
                          onClick={() => updateCommandBuilder(index, amount)}
                        >
                          {amount}
                        </EnhancedButton>
                      ))}
                      <EnhancedInput
                        name="custom-amount"
                        placeholder="Custom amount"
                        size="md"
                        inputType="number"
                        onKeyPress={(e) => {
                          if (e.key === "Enter") {
                            const target = e.target as HTMLInputElement;
                            updateCommandBuilder(index, target.value);
                          }
                        }}
                      />
                    </HStack>
                  )}

                  {step.type === "token" && (
                    <SimpleGrid columns={4} spacing={3}>
                      {[
                        "ETH",
                        "USDC",
                        "WETH",
                        "WBTC",
                        "DAI",
                        "MATIC",
                        "LINK",
                        "UNI",
                      ].map((token) => (
                        <EnhancedButton
                          key={token}
                          variant={step.value === token ? "solid" : "outline"}
                          colorScheme={step.value === token ? "blue" : "gray"}
                          size="md"
                          onClick={() => updateCommandBuilder(index, token)}
                        >
                          {token}
                        </EnhancedButton>
                      ))}
                    </SimpleGrid>
                  )}

                  {step.type === "address" && (
                    <VStack spacing={3} align="stretch">
                      {["vitalik.eth", "snel.eth"].map((address) => (
                        <EnhancedButton
                          key={address}
                          variant={step.value === address ? "solid" : "outline"}
                          colorScheme={step.value === address ? "blue" : "gray"}
                          size="md"
                          onClick={() => updateCommandBuilder(index, address)}
                          leftIcon={<FaWallet />}
                        >
                          {address}
                        </EnhancedButton>
                      ))}
                      <EnhancedInput
                        name="custom-address"
                        placeholder="Custom address or ENS"
                        size="md"
                        onKeyPress={(e) => {
                          if (e.key === "Enter") {
                            const target = e.target as HTMLInputElement;
                            updateCommandBuilder(index, target.value);
                          }
                        }}
                      />
                    </VStack>
                  )}

                  {step.type === "chain" && (
                    <SimpleGrid columns={2} spacing={3}>
                      {Object.values(SUPPORTED_CHAINS).map((chain) => (
                        <EnhancedButton
                          key={chain}
                          variant={step.value === chain ? "solid" : "outline"}
                          colorScheme={step.value === chain ? "blue" : "gray"}
                          size="md"
                          onClick={() => updateCommandBuilder(index, chain)}
                          leftIcon={<FaLink />}
                        >
                          {chain}
                        </EnhancedButton>
                      ))}
                    </SimpleGrid>
                  )}
                </Box>
              ))}
            </VStack>
          </Box>

          <Box
            p={4}
            borderWidth="1px"
            borderRadius="md"
            bg={commandBuilderBgColor}
          >
            <Text fontWeight="medium" mb={2}>
              Preview:
            </Text>
            <Text fontSize="lg">
              {commandBuilderSteps
                .map((step) => step.value)
                .filter(Boolean)
                .join(" ")}
              {commandBuilderSteps[0].value === "swap" &&
                commandBuilderSteps.length > 2 &&
                commandBuilderSteps[2].value &&
                " for"}
              {commandBuilderSteps[0].value === "send" &&
                commandBuilderSteps.length > 2 &&
                commandBuilderSteps[2].value &&
                " to"}
              {commandBuilderSteps[0].value === "bridge" &&
                commandBuilderSteps.length > 2 &&
                commandBuilderSteps[2].value &&
                " to"}
            </Text>
          </Box>
        </VStack>
      </EnhancedModal>
    </Box>
  );
};

export default EnhancedCommandInput;
