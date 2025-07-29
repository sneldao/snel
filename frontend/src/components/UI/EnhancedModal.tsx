import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  createContext,
  useContext,
} from "react";
import Image from 'next/image';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Box,
  Flex,
  Text,
  Heading,
  Stack,
  HStack,
  VStack,
  Divider,
  IconButton,
  Collapse,
  useDisclosure,
  useColorModeValue,
  useTheme,
  Portal,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  DrawerFooter,
  Tooltip,
  Badge,
  Progress,
  Spinner,
  Input,
  InputGroup,
  InputRightElement,
  Switch,
  Kbd,
  VisuallyHidden,
  useBreakpointValue,
  Slide,
  ScaleFade,
  SlideFade,
  Fade,
  chakra,
  forwardRef,
  StylesProvider,
  useMultiStyleConfig,
  useStyles,
  ThemingProps,
  SystemProps,
  ResponsiveValue,
} from "@chakra-ui/react";
import {
  motion,
  AnimatePresence,
  useAnimation,
  Variants,
  PanInfo,
  useDragControls,
} from "framer-motion";
import { FocusScope, useFocusManager } from "@react-aria/focus";
import { usePreventScroll } from "@react-aria/overlays";
import { RemoveScroll } from "react-remove-scroll";
import { createFocusTrap } from "focus-trap";
import {
  FaTimes,
  FaChevronLeft,
  FaChevronRight,
  FaCheck,
  FaExclamationTriangle,
  FaInfoCircle,
  FaQuestionCircle,
  FaWallet,
  FaExchangeAlt,
  FaCog,
  FaPercentage,
  FaArrowUp,
  FaArrowDown,
  FaArrowLeft,
  FaArrowRight,
  FaExpand,
  FaCompress,
  FaGripLines,
  FaLock,
  FaUnlock,
  FaEthereum,
  FaBitcoin,
  FaChevronDown,
  FaChevronUp,
  FaEllipsisH,
  FaRegCopy,
  FaExternalLinkAlt,
} from "react-icons/fa";
import { useHotkeys } from "react-hotkeys-hook";

// ========== Types & Interfaces ==========

export type ModalVariant =
  | "default"
  | "centered"
  | "full"
  | "drawer"
  | "popup"
  | "sheet";

export type ModalSize = "xs" | "sm" | "md" | "lg" | "xl" | "full";

export type ModalPlacement = "top" | "right" | "bottom" | "left" | "center";

export type AnimationType =
  | "fade"
  | "slide"
  | "scale"
  | "bounce"
  | "rotate"
  | "none";

export type ModalState = "idle" | "loading" | "success" | "error" | "warning";

export type ConfirmationType =
  | "info"
  | "success"
  | "warning"
  | "error"
  | "question";

export type StepStatus = "incomplete" | "current" | "complete" | "error";

export interface ModalAction {
  label: string;
  onClick: () => void;
  variant?: string;
  colorScheme?: string;
  isDisabled?: boolean;
  isLoading?: boolean;
  icon?: React.ReactNode;
  shortcut?: string;
  tooltip?: string;
  closeOnClick?: boolean;
}

export interface ModalSection {
  id: string;
  title: string;
  content: React.ReactNode;
  isCollapsible?: boolean;
  isInitiallyExpanded?: boolean;
  icon?: React.ReactNode;
}

export interface FormStep {
  id: string;
  title: string;
  description?: string;
  content: React.ReactNode;
  status: StepStatus;
  isOptional?: boolean;
  validationFn?: () => boolean | Promise<boolean>;
  onEnter?: () => void;
  onExit?: () => void;
}

export interface WalletInfo {
  id: string;
  name: string;
  icon?: React.ReactNode | string;
  description?: string;
  isInstalled?: boolean;
  isConnecting?: boolean;
  isConnected?: boolean;
  onClick?: () => void;
}

export interface TransactionDetails {
  from: string;
  to: string;
  value: string;
  gasLimit?: string;
  gasPrice?: string;
  nonce?: number;
  data?: string;
  chainId?: number;
  estimatedTime?: string;
  estimatedFee?: string;
}

export interface SwapSettings {
  slippage: number;
  deadline: number;
  autoRouter: boolean;
  expertMode: boolean;
  multihop: boolean;
}

export interface EnhancedModalProps {
  // Base props
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;

  // Styling props
  variant?: ModalVariant;
  size?: ModalSize;
  placement?: ModalPlacement;
  state?: ModalState;

  // Animation props
  animation?: AnimationType;
  animationDuration?: number;
  animationDelay?: number;

  // Header props
  showHeader?: boolean;
  headerActions?: ModalAction[];
  headerIcon?: React.ReactNode;

  // Footer props
  showFooter?: boolean;
  primaryAction?: ModalAction;
  secondaryAction?: ModalAction;
  additionalActions?: ModalAction[];

  // Close behavior props
  closeOnEsc?: boolean;
  closeOnOverlayClick?: boolean;
  showCloseButton?: boolean;
  preventClose?: boolean;

  // Interactive props
  isDraggable?: boolean;
  isResizable?: boolean;
  initialPosition?: { x: number; y: number };

  // Overlay props
  overlayBlur?: string;
  overlayColor?: string;
  overlayOpacity?: number;

  // Specialized modal props
  isConfirmationModal?: boolean;
  confirmationType?: ConfirmationType;
  confirmationMessage?: string;

  // Multi-step form props
  steps?: FormStep[];
  initialStep?: number;
  showStepIndicator?: boolean;

  // Collapsible sections
  sections?: ModalSection[];

  // DeFi specific props
  isWalletModal?: boolean;
  wallets?: WalletInfo[];

  isTransactionModal?: boolean;
  transaction?: TransactionDetails;

  isSwapSettingsModal?: boolean;
  swapSettings?: SwapSettings;
  onSwapSettingsChange?: (settings: SwapSettings) => void;

  // Keyboard shortcuts
  shortcuts?: { [key: string]: () => void };

  // Accessibility props
  ariaLabel?: string;
  ariaDescribedBy?: string;
  initialFocusRef?: React.RefObject<HTMLElement>;
  finalFocusRef?: React.RefObject<HTMLElement>;
  returnFocusOnClose?: boolean;

  // Stack management
  zIndex?: number;
  id?: string;

  // Callback props
  onAnimationComplete?: () => void;
  onDragEnd?: (info: PanInfo) => void;
  onResize?: (width: number, height: number) => void;
  onStepChange?: (stepIndex: number) => void;

  // Additional props
  [key: string]: any;
}

// ========== Context ==========

interface ModalContextValue {
  currentStep: number;
  totalSteps: number;
  goToStep: (step: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  isLastStep: boolean;
  isFirstStep: boolean;
  closeModal: () => void;
  modalState: ModalState;
  setModalState: (state: ModalState) => void;
}

const ModalContext = createContext<ModalContextValue | undefined>(undefined);

const useModalContext = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error("useModalContext must be used within a ModalProvider");
  }
  return context;
};

// ========== Animation Variants ==========

const fadeVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

const slideVariants: Variants = {
  hidden: (placement: ModalPlacement) => {
    switch (placement) {
      case "top":
        return { y: "-100%", opacity: 0 };
      case "right":
        return { x: "100%", opacity: 0 };
      case "bottom":
        return { y: "100%", opacity: 0 };
      case "left":
        return { x: "-100%", opacity: 0 };
      default:
        return { y: 20, opacity: 0 };
    }
  },
  visible: {
    x: 0,
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 300,
    },
  },
  exit: (placement: ModalPlacement) => {
    switch (placement) {
      case "top":
        return { y: "-100%", opacity: 0, transition: { duration: 0.2 } };
      case "right":
        return { x: "100%", opacity: 0, transition: { duration: 0.2 } };
      case "bottom":
        return { y: "100%", opacity: 0, transition: { duration: 0.2 } };
      case "left":
        return { x: "-100%", opacity: 0, transition: { duration: 0.2 } };
      default:
        return { y: 20, opacity: 0, transition: { duration: 0.2 } };
    }
  },
};

const scaleVariants: Variants = {
  hidden: { scale: 0.8, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 300,
    },
  },
  exit: { scale: 0.8, opacity: 0, transition: { duration: 0.2 } },
};

const bounceVariants: Variants = {
  hidden: { scale: 0.8, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 8,
      stiffness: 300,
      velocity: 2,
    },
  },
  exit: { scale: 0.8, opacity: 0, transition: { duration: 0.2 } },
};

const rotateVariants: Variants = {
  hidden: { rotate: -15, scale: 0.8, opacity: 0 },
  visible: {
    rotate: 0,
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 20,
      stiffness: 300,
    },
  },
  exit: { rotate: 15, scale: 0.8, opacity: 0, transition: { duration: 0.2 } },
};

const drawerVariants: Variants = {
  hidden: (placement: ModalPlacement) => {
    switch (placement) {
      case "top":
        return { y: "-100%" };
      case "right":
        return { x: "100%" };
      case "bottom":
        return { y: "100%" };
      case "left":
        return { x: "-100%" };
      default:
        return { x: "100%" };
    }
  },
  visible: {
    x: 0,
    y: 0,
    transition: {
      type: "spring",
      damping: 30,
      stiffness: 300,
    },
  },
  exit: (placement: ModalPlacement) => {
    switch (placement) {
      case "top":
        return { y: "-100%", transition: { duration: 0.3 } };
      case "right":
        return { x: "100%", transition: { duration: 0.3 } };
      case "bottom":
        return { y: "100%", transition: { duration: 0.3 } };
      case "left":
        return { x: "-100%", transition: { duration: 0.3 } };
      default:
        return { x: "100%", transition: { duration: 0.3 } };
    }
  },
};

const sheetVariants: Variants = {
  hidden: { y: "100%" },
  visible: {
    y: 0,
    transition: {
      type: "spring",
      damping: 30,
      stiffness: 300,
    },
  },
  exit: { y: "100%", transition: { duration: 0.3 } },
};

const popupVariants: Variants = {
  hidden: { scale: 0.9, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      damping: 25,
      stiffness: 300,
    },
  },
  exit: { scale: 0.9, opacity: 0, transition: { duration: 0.2 } },
};

const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.2, delay: 0.1 } },
};

const stepIndicatorVariants: Variants = {
  incomplete: { opacity: 0.4, scale: 0.9 },
  current: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 },
  },
  complete: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 },
  },
  error: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 },
  },
};

// ========== Helper Components ==========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionDrawerContent = motion(DrawerContent);

// Modal Backdrop with blur effect
const EnhancedBackdrop: React.FC<{
  onClick: () => void;
  isOpen: boolean;
  overlayColor?: string;
  overlayOpacity?: number;
  overlayBlur?: string;
}> = ({
  onClick,
  isOpen,
  overlayColor,
  overlayOpacity = 0.6,
  overlayBlur = "2px",
}) => {
  // Pre-compute the default background color to avoid a conditional hook call
  const defaultBgColor = useColorModeValue("blackAlpha.600", "blackAlpha.700");
  const bgColor = overlayColor || defaultBgColor;

  return (
    <AnimatePresence>
      {isOpen && (
        <MotionBox
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg={bgColor}
          backdropFilter={`blur(${overlayBlur})`}
          opacity={overlayOpacity}
          onClick={onClick}
          zIndex="overlay"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        />
      )}
    </AnimatePresence>
  );
};

// Step Indicator for multi-step forms
const StepIndicator: React.FC<{
  steps: FormStep[];
  currentStep: number;
  onClick?: (index: number) => void;
}> = ({ steps, currentStep, onClick }) => {
  const activeColor = useColorModeValue("blue.500", "blue.300");
  const completeColor = useColorModeValue("green.500", "green.300");
  const errorColor = useColorModeValue("red.500", "red.300");
  const inactiveColor = useColorModeValue("gray.300", "gray.600");
  const textColor = useColorModeValue("gray.700", "gray.200");
  // background for each step circle – pre-compute to avoid hook in map render
  const circleBg = useColorModeValue("white", "gray.800");

  return (
    <Box width="100%" mb={6}>
      <Flex justify="space-between" align="center" position="relative">
        {/* Progress Line */}
        <Box
          position="absolute"
          height="2px"
          bg={inactiveColor}
          left="0"
          right="0"
          top="50%"
          transform="translateY(-50%)"
          zIndex={0}
        />

        {/* Completed Line */}
        <Box
          position="absolute"
          height="2px"
          bg={activeColor}
          left="0"
          width={`${(currentStep / (steps.length - 1)) * 100}%`}
          top="50%"
          transform="translateY(-50%)"
          zIndex={1}
          transition="width 0.3s ease"
        />

        {/* Steps */}
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isComplete = index < currentStep;
          const isError = step.status === "error";

          const getStepColor = () => {
            if (isError) return errorColor;
            if (isComplete) return completeColor;
            if (isActive) return activeColor;
            return inactiveColor;
          };

          const getStepStatus = () => {
            if (isError) return "error";
            if (isComplete) return "complete";
            if (isActive) return "current";
            return "incomplete";
          };

          return (
            <MotionFlex
              key={step.id}
              direction="column"
              align="center"
              zIndex={2}
              cursor={onClick ? "pointer" : "default"}
              onClick={() => onClick && onClick(index)}
              variants={stepIndicatorVariants}
              initial="incomplete"
              animate={getStepStatus()}
            >
              <Flex
                width="32px"
                height="32px"
                borderRadius="full"
                bg={circleBg}
                border="2px solid"
                borderColor={getStepColor()}
                align="center"
                justify="center"
                fontWeight="bold"
                color={getStepColor()}
                position="relative"
              >
                {isComplete ? (
                  <FaCheck />
                ) : isError ? (
                  <FaExclamationTriangle />
                ) : (
                  <Text>{index + 1}</Text>
                )}
              </Flex>

              <Text
                fontSize="sm"
                fontWeight={isActive ? "bold" : "normal"}
                color={isActive ? textColor : "gray.500"}
                mt={2}
                textAlign="center"
                maxWidth="80px"
              >
                {step.title}
              </Text>

              {step.description && (
                <Text
                  fontSize="xs"
                  color="gray.500"
                  mt={1}
                  textAlign="center"
                  maxWidth="80px"
                >
                  {step.description}
                </Text>
              )}
            </MotionFlex>
          );
        })}
      </Flex>
    </Box>
  );
};

// Collapsible Section
const CollapsibleSection: React.FC<{
  section: ModalSection;
}> = ({ section }) => {
  const { isOpen, onToggle } = useDisclosure({
    defaultIsOpen: section.isInitiallyExpanded !== false,
  });

  // Pre-compute colors used in props to satisfy hook rules
  const sectionBg = useColorModeValue("gray.50", "gray.800");
  const sectionHoverBg = useColorModeValue("gray.100", "gray.700");

  return (
    <Box mb={4}>
      <Flex
        justify="space-between"
        align="center"
        py={3}
        px={2}
        borderWidth="1px"
        borderRadius="md"
        cursor={section.isCollapsible ? "pointer" : "default"}
        onClick={section.isCollapsible ? onToggle : undefined}
        bg={sectionBg}
        _hover={section.isCollapsible ? { bg: sectionHoverBg } : {}}
      >
        <Flex align="center">
          {section.icon && <Box mr={3}>{section.icon}</Box>}
          <Heading size="sm">{section.title}</Heading>
        </Flex>

        {section.isCollapsible && (
          <Box
            transform={isOpen ? "rotate(180deg)" : "none"}
            transition="transform 0.2s"
          >
            <FaChevronDown />
          </Box>
        )}
      </Flex>

      <Collapse in={!section.isCollapsible || isOpen} animateOpacity>
        <Box pt={4} px={2}>
          {section.content}
        </Box>
      </Collapse>
    </Box>
  );
};

// Wallet Connection Modal Content
const WalletConnectionContent: React.FC<{
  wallets: WalletInfo[];
}> = ({ wallets }) => {
  const walletBg = useColorModeValue("white", "gray.800");
  const walletHoverBg = useColorModeValue("gray.50", "gray.700");
  return (
    <VStack spacing={4} align="stretch">
      {wallets.map((wallet) => (
        <Flex
          key={wallet.id}
          p={4}
          borderWidth="1px"
          borderRadius="md"
          align="center"
          justify="space-between"
          cursor={wallet.onClick ? "pointer" : "default"}
          onClick={wallet.onClick}
          bg={walletBg}
          _hover={wallet.onClick ? { bg: walletHoverBg } : {}}
          opacity={!wallet.isInstalled ? 0.6 : 1}
        >
          <Flex align="center">
            <Box mr={4} fontSize="2xl">
              {typeof wallet.icon === "string" ? (
                <Image
                  src={wallet.icon as string}
                  alt={wallet.name}
                  width={40}
                  height={40}
                />
              ) : (
                wallet.icon || <FaWallet />
              )}
            </Box>

            <Box>
              <Text fontWeight="bold">{wallet.name}</Text>
              {wallet.description && (
                <Text fontSize="sm" color="gray.500">
                  {wallet.description}
                </Text>
              )}
            </Box>
          </Flex>

          <Box>
            {wallet.isConnecting ? (
              <Spinner size="sm" />
            ) : wallet.isConnected ? (
              <Badge colorScheme="green">Connected</Badge>
            ) : !wallet.isInstalled ? (
              <Badge colorScheme="yellow">Not Installed</Badge>
            ) : (
              <FaArrowRight />
            )}
          </Box>
        </Flex>
      ))}
    </VStack>
  );
};

// Transaction Confirmation Modal Content
const TransactionConfirmationContent: React.FC<{
  transaction: TransactionDetails;
}> = ({ transaction }) => {
  const {
    from,
    to,
    value,
    gasLimit,
    gasPrice,
    nonce,
    data,
    chainId,
    estimatedTime,
    estimatedFee,
  } = transaction;

  // ------------------------------------------------------------------
  // Theme-aware colors pre-computed at component level to satisfy
  // React-Hook rules (hooks cannot be called conditionally / in JSX)
  // ------------------------------------------------------------------
  const dataBgColor = useColorModeValue("gray.100", "gray.900");
  const warningBgColor = useColorModeValue("yellow.50", "yellow.900");
  const warningTextColor = useColorModeValue("yellow.800", "yellow.200");

  const formatAddress = (address: string) => {
    return `${address.substring(0, 6)}...${address.substring(
      address.length - 4
    )}`;
  };

  return (
    <VStack spacing={4} align="stretch">
      <Box
        p={4}
        borderWidth="1px"
        borderRadius="md"
        bg={useColorModeValue("gray.50", "gray.800")}
      >
        <Heading size="sm" mb={3}>
          Transaction Details
        </Heading>

        <VStack spacing={3} align="stretch">
          <Flex justify="space-between">
            <Text color="gray.500">From</Text>
            <HStack>
              <Text fontWeight="medium">{formatAddress(from)}</Text>
              <IconButton
                aria-label="Copy address"
                icon={<FaRegCopy />}
                size="xs"
                variant="ghost"
              />
            </HStack>
          </Flex>

          <Flex justify="space-between">
            <Text color="gray.500">To</Text>
            <HStack>
              <Text fontWeight="medium">{formatAddress(to)}</Text>
              <IconButton
                aria-label="Copy address"
                icon={<FaRegCopy />}
                size="xs"
                variant="ghost"
              />
            </HStack>
          </Flex>

          <Flex justify="space-between">
            <Text color="gray.500">Value</Text>
            <Text fontWeight="medium">{value} ETH</Text>
          </Flex>

          {estimatedFee && (
            <Flex justify="space-between">
              <Text color="gray.500">Estimated Fee</Text>
              <Text fontWeight="medium">{estimatedFee}</Text>
            </Flex>
          )}

          {estimatedTime && (
            <Flex justify="space-between">
              <Text color="gray.500">Estimated Time</Text>
              <Text fontWeight="medium">{estimatedTime}</Text>
            </Flex>
          )}
        </VStack>
      </Box>

      <CollapsibleSection
        section={{
          id: "advanced",
          title: "Advanced Details",
          content: (
            <VStack spacing={3} align="stretch">
              {gasLimit && (
                <Flex justify="space-between">
                  <Text color="gray.500">Gas Limit</Text>
                  <Text fontWeight="medium">{gasLimit}</Text>
                </Flex>
              )}

              {gasPrice && (
                <Flex justify="space-between">
                  <Text color="gray.500">Gas Price</Text>
                  <Text fontWeight="medium">{gasPrice}</Text>
                </Flex>
              )}

              {nonce !== undefined && (
                <Flex justify="space-between">
                  <Text color="gray.500">Nonce</Text>
                  <Text fontWeight="medium">{nonce}</Text>
                </Flex>
              )}

              {chainId && (
                <Flex justify="space-between">
                  <Text color="gray.500">Chain ID</Text>
                  <Text fontWeight="medium">{chainId}</Text>
                </Flex>
              )}

              {data && (
                <Box>
                  <Text color="gray.500" mb={1}>
                    Data
                  </Text>
                  {/* Pre-compute background color to satisfy hook rules */}
                  {/*
                    Rule: React hooks must not be called conditionally or
                    within callbacks/JSX.  We therefore call the hook once
                    at component level and reference the value here.
                  */}
                  <Box
                    p={2}
                    borderWidth="1px"
                    borderRadius="md"
                    bg={dataBgColor}
                    fontSize="sm"
                    fontFamily="monospace"
                    wordBreak="break-all"
                  >
                    {data}
                  </Box>
                </Box>
              )}
            </VStack>
          ),
          isCollapsible: true,
          isInitiallyExpanded: false,
          icon: <FaCog />,
        }}
      />

      <Box
        p={4}
        borderWidth="1px"
        borderRadius="md"
        bg={warningBgColor}
        color={warningTextColor}
      >
        <Flex align="center">
          <Box as={FaExclamationTriangle} mr={2} />
          <Text fontWeight="medium">
            Always verify transaction details before confirming
          </Text>
        </Flex>
      </Box>
    </VStack>
  );
};

// Swap Settings Modal Content
const SwapSettingsContent: React.FC<{
  settings: SwapSettings;
  onChange: (settings: SwapSettings) => void;
}> = ({ settings, onChange }) => {
  const [localSettings, setLocalSettings] = useState<SwapSettings>(settings);

  // Pre-compute colors to avoid conditional hook calls
  const warningBgColor = useColorModeValue("red.50", "red.900");
  const warningTextColor = useColorModeValue("red.800", "red.200");

  const handleSlippageChange = (value: number) => {
    const newSettings = { ...localSettings, slippage: value };
    setLocalSettings(newSettings);
    onChange(newSettings);
  };

  const handleDeadlineChange = (value: number) => {
    const newSettings = { ...localSettings, deadline: value };
    setLocalSettings(newSettings);
    onChange(newSettings);
  };

  const handleToggleChange = (key: keyof SwapSettings) => {
    const newSettings = { ...localSettings, [key]: !localSettings[key] };
    setLocalSettings(newSettings);
    onChange(newSettings);
  };

  return (
    <VStack spacing={6} align="stretch">
      <Box>
        <Flex justify="space-between" align="center" mb={2}>
          <Text fontWeight="medium">Slippage Tolerance</Text>
          <Tooltip label="Your transaction will revert if the price changes unfavorably by more than this percentage">
            <Box as={FaInfoCircle} color="gray.500" />
          </Tooltip>
        </Flex>

        <HStack spacing={2} mb={2}>
          {[0.1, 0.5, 1.0].map((value) => (
            <Button
              key={value}
              size="sm"
              variant={localSettings.slippage === value ? "solid" : "outline"}
              colorScheme={localSettings.slippage === value ? "blue" : "gray"}
              onClick={() => handleSlippageChange(value)}
            >
              {value}%
            </Button>
          ))}

          <InputGroup size="sm" width="100px">
            <Input
              type="number"
              value={localSettings.slippage}
              onChange={(e) =>
                handleSlippageChange(parseFloat(e.target.value) || 0)
              }
              min={0.1}
              max={50}
              step={0.1}
            />
            <InputRightElement>%</InputRightElement>
          </InputGroup>
        </HStack>

        {localSettings.slippage > 5 && (
          <Text color="red.500" fontSize="sm">
            High slippage increases the risk of price impact
          </Text>
        )}
        {localSettings.slippage < 0.5 && (
          <Text color="yellow.500" fontSize="sm">
            Low slippage may cause transaction to fail
          </Text>
        )}
      </Box>

      <Box>
        <Flex justify="space-between" align="center" mb={2}>
          <Text fontWeight="medium">Transaction Deadline</Text>
          <Tooltip label="Your transaction will revert if it is pending for more than this period of time">
            <Box as={FaInfoCircle} color="gray.500" />
          </Tooltip>
        </Flex>

        <HStack spacing={2}>
          <InputGroup size="sm" width="100px">
            <Input
              type="number"
              value={localSettings.deadline}
              onChange={(e) =>
                handleDeadlineChange(parseInt(e.target.value) || 20)
              }
              min={1}
              max={180}
              step={1}
            />
          </InputGroup>
          <Text>minutes</Text>
        </HStack>
      </Box>

      <Divider />

      <VStack spacing={4} align="stretch">
        <Flex justify="space-between" align="center">
          <HStack>
            <Text fontWeight="medium">Auto Router</Text>
            <Tooltip label="Automatically finds the best trade route">
              <Box as={FaInfoCircle} color="gray.500" />
            </Tooltip>
          </HStack>
          <Switch
            isChecked={localSettings.autoRouter}
            onChange={() => handleToggleChange("autoRouter")}
          />
        </Flex>

        <Flex justify="space-between" align="center">
          <HStack>
            <Text fontWeight="medium">Multi-hop Trades</Text>
            <Tooltip label="Allow multiple hops between tokens">
              <Box as={FaInfoCircle} color="gray.500" />
            </Tooltip>
          </HStack>
          <Switch
            isChecked={localSettings.multihop}
            onChange={() => handleToggleChange("multihop")}
          />
        </Flex>

        <Flex justify="space-between" align="center">
          <HStack>
            <Text fontWeight="medium">Expert Mode</Text>
            <Badge colorScheme="red">Advanced</Badge>
          </HStack>
          <Switch
            isChecked={localSettings.expertMode}
            onChange={() => handleToggleChange("expertMode")}
          />
        </Flex>

        {localSettings.expertMode && (
          <Box
            p={3}
            borderWidth="1px"
            borderRadius="md"
            bg={warningBgColor}
            color={warningTextColor}
          >
            <Text fontSize="sm">
              Expert mode turns off the confirm transaction prompt and allows
              high slippage trades that often result in bad rates and lost
              funds.
            </Text>
          </Box>
        )}
      </VStack>
    </VStack>
  );
};

// Confirmation Modal Content
const ConfirmationContent: React.FC<{
  type: ConfirmationType;
  message: string;
}> = ({ type, message }) => {
  const getIcon = () => {
    switch (type) {
      case "info":
        return FaInfoCircle;
      case "success":
        return FaCheck;
      case "warning":
        return FaExclamationTriangle;
      case "error":
        return FaTimes;
      case "question":
        return FaQuestionCircle;
      default:
        return FaInfoCircle;
    }
  };

  // ------------------------------------------------------------
  // Pre-compute all possible colors once per render to satisfy
  // React-Hook rules (hooks must be at component level only).
  // ------------------------------------------------------------
  const infoColor = useColorModeValue("blue.500", "blue.300");
  const successColor = useColorModeValue("green.500", "green.300");
  const warningColor = useColorModeValue("orange.500", "orange.300");
  const errorColor = useColorModeValue("red.500", "red.300");
  const questionColor = useColorModeValue("purple.500", "purple.300");

  const colorMap: Record<ConfirmationType, string> = {
    info: infoColor,
    success: successColor,
    warning: warningColor,
    error: errorColor,
    question: questionColor,
  };

  const Icon = getIcon();
  const color = colorMap[type] ?? infoColor;

  return (
    <Flex direction="column" align="center" py={4}>
      <Box as={Icon} fontSize="4xl" color={color} mb={4} />
      <Text textAlign="center" fontSize="lg">
        {message}
      </Text>
    </Flex>
  );
};

// Keyboard shortcuts help
const KeyboardShortcutsHelp: React.FC<{
  shortcuts: { [key: string]: () => void };
  isOpen: boolean;
  onClose: () => void;
}> = ({ shortcuts, isOpen, onClose }) => {
  const shortcutEntries = Object.entries(shortcuts);

  // Pre-compute background color to avoid conditional hook calls
  const helpBgColor = useColorModeValue("white", "gray.800");

  return (
    <ScaleFade in={isOpen}>
      <Box
        position="absolute"
        bottom="20px"
        right="20px"
        bg={helpBgColor}
        boxShadow="lg"
        borderRadius="md"
        p={4}
        maxWidth="300px"
        zIndex={1500}
      >
        <Flex justify="space-between" align="center" mb={3}>
          <Heading size="sm">Keyboard Shortcuts</Heading>
          <IconButton
            aria-label="Close shortcuts help"
            icon={<FaTimes />}
            size="sm"
            variant="ghost"
            onClick={onClose}
          />
        </Flex>

        <VStack spacing={2} align="stretch">
          {shortcutEntries.map(([key, _]) => {
            // Convert key to display format
            const displayKey = key
              .replace("shift+", "⇧+")
              .replace("ctrl+", "⌃+")
              .replace("alt+", "⌥+")
              .replace("meta+", "⌘+")
              .replace("escape", "Esc")
              .toUpperCase();

            // Get description (key name without modifiers)
            const description = key.split("+").pop() || key;

            return (
              <Flex key={key} justify="space-between" align="center">
                <Text fontSize="sm" textTransform="capitalize">
                  {description}
                </Text>
                <Kbd>{displayKey}</Kbd>
              </Flex>
            );
          })}
        </VStack>
      </Box>
    </ScaleFade>
  );
};

// ========== Main Component ==========

export const EnhancedModal = forwardRef<HTMLDivElement, EnhancedModalProps>(
  (props, ref) => {
    const {
      // Base props
      isOpen,
      onClose,
      title,
      subtitle,
      children,

      // Styling props
      variant = "default",
      size = "md",
      placement = "center",
      state = "idle",

      // Animation props
      animation = "fade",
      animationDuration = 0.3,
      animationDelay = 0,

      // Header props
      showHeader = true,
      headerActions,
      headerIcon,

      // Footer props
      showFooter = true,
      primaryAction,
      secondaryAction,
      additionalActions,

      // Close behavior props
      closeOnEsc = true,
      closeOnOverlayClick = true,
      showCloseButton = true,
      preventClose = false,

      // Interactive props
      isDraggable = false,
      isResizable = false,
      initialPosition,

      // Overlay props
      overlayBlur = "2px",
      overlayColor,
      overlayOpacity = 0.6,

      // Specialized modal props
      isConfirmationModal = false,
      confirmationType = "info",
      confirmationMessage = "",

      // Multi-step form props
      steps = [],
      initialStep = 0,
      showStepIndicator = true,

      // Collapsible sections
      sections = [],

      // DeFi specific props
      isWalletModal = false,
      wallets = [],

      isTransactionModal = false,
      transaction,

      isSwapSettingsModal = false,
      swapSettings,
      onSwapSettingsChange,

      // Keyboard shortcuts
      shortcuts = {},

      // Accessibility props
      ariaLabel,
      ariaDescribedBy,
      initialFocusRef,
      finalFocusRef,
      returnFocusOnClose = true,

      // Stack management
      zIndex,
      id,

      // Callback props
      onAnimationComplete,
      onDragEnd,
      onResize,
      onStepChange,

      // Additional props
      ...rest
    } = props;

    // State
    const [currentStep, setCurrentStep] = useState(initialStep);
    const [modalState, setModalState] = useState<ModalState>(state);
    const [position, setPosition] = useState(initialPosition || { x: 0, y: 0 });
    const [size2D, setSize2D] = useState({ width: 0, height: 0 });
    const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

    // Refs
    const modalRef = useRef<HTMLDivElement>(null);
    const dragControls = useDragControls();
    const combinedRef = useCallback(
      (node: HTMLDivElement) => {
        // Set modal ref
        modalRef.current = node;

        // Forward ref
        if (typeof ref === "function") {
          ref(node);
        } else if (ref) {
          (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
        }
      },
      [ref]
    );

    // Hooks
    const theme = useTheme();
    const isMobile = useBreakpointValue({ base: true, md: false });

    // Prevent body scroll when modal is open
    usePreventScroll({ isDisabled: !isOpen });

    // Register keyboard shortcuts
    useHotkeys("shift+?", () => setShowKeyboardHelp((prev) => !prev), []);
    useHotkeys(
      "escape",
      () => {
        if (isOpen && closeOnEsc && !preventClose) {
          onClose();
        }
      },
      [isOpen, closeOnEsc, preventClose, onClose]
    );

    // Register custom shortcuts in a single hook to comply with React Hook rules
    useHotkeys(
      Object.keys(shortcuts), // array of shortcut key combos
      (e, handler) => {
        const combo = Array.isArray(handler.keys)
          ? handler.keys.join("+")
          : handler.keys || "";

        const shortcutAction = shortcuts[combo];

        if (shortcutAction && isOpen) {
          e.preventDefault();
          shortcutAction();
        }
      },
      [isOpen, shortcuts]
    );

    // Effects

    // Update step if initialStep changes
    useEffect(() => {
      setCurrentStep(initialStep);
    }, [initialStep]);

    // Update modal state if state prop changes
    useEffect(() => {
      setModalState(state);
    }, [state]);

    // Set up focus trap when modal opens
    useEffect(() => {
      if (isOpen && modalRef.current) {
        const trap = createFocusTrap(modalRef.current, {
          initialFocus: initialFocusRef?.current || undefined,
          fallbackFocus: modalRef.current,
          escapeDeactivates: closeOnEsc && !preventClose,
          returnFocusOnDeactivate: returnFocusOnClose,
        });

        trap.activate();

        return () => {
          trap.deactivate();
        };
      }
    }, [isOpen, initialFocusRef, closeOnEsc, preventClose, returnFocusOnClose]);

    // Handlers

    const handleClose = () => {
      if (!preventClose) {
        onClose();
      }
    };

    const handleOverlayClick = () => {
      if (closeOnOverlayClick && !preventClose) {
        onClose();
      }
    };

    const handleDragStart = (event: React.PointerEvent<HTMLDivElement>) => {
      if (isDraggable) {
        dragControls.start(event);
      }
    };

    const handleDragEnd = (info: PanInfo) => {
      setPosition({
        x: position.x + info.offset.x,
        y: position.y + info.offset.y,
      });

      if (onDragEnd) {
        onDragEnd(info);
      }
    };

    const handleResize = (width: number, height: number) => {
      setSize2D({ width, height });

      if (onResize) {
        onResize(width, height);
      }
    };

    const goToStep = (step: number) => {
      if (step >= 0 && step < steps.length) {
        setCurrentStep(step);

        if (onStepChange) {
          onStepChange(step);
        }
      }
    };

    const nextStep = () => {
      if (currentStep < steps.length - 1) {
        goToStep(currentStep + 1);
      }
    };

    const prevStep = () => {
      if (currentStep > 0) {
        goToStep(currentStep - 1);
      }
    };

    // Helper functions

    const getModalVariant = () => {
      switch (animation) {
        case "fade":
          return fadeVariants;
        case "slide":
          return slideVariants;
        case "scale":
          return scaleVariants;
        case "bounce":
          return bounceVariants;
        case "rotate":
          return rotateVariants;
        default:
          return fadeVariants;
      }
    };

    const getModalSize = () => {
      // For drawer and sheet variants
      if (variant === "drawer") {
        switch (size) {
          case "xs":
            return { width: "280px", height: "100%" };
          case "sm":
            return { width: "320px", height: "100%" };
          case "md":
            return { width: "380px", height: "100%" };
          case "lg":
            return { width: "440px", height: "100%" };
          case "xl":
            return { width: "520px", height: "100%" };
          case "full":
            return { width: "100%", height: "100%" };
          default:
            return { width: "380px", height: "100%" };
        }
      }

      if (variant === "sheet") {
        switch (size) {
          case "xs":
            return { width: "100%", height: "20%" };
          case "sm":
            return { width: "100%", height: "30%" };
          case "md":
            return { width: "100%", height: "50%" };
          case "lg":
            return { width: "100%", height: "70%" };
          case "xl":
            return { width: "100%", height: "85%" };
          case "full":
            return { width: "100%", height: "100%" };
          default:
            return { width: "100%", height: "50%" };
        }
      }

      // For standard modal variants
      switch (size) {
        case "xs":
          return { width: "320px", maxWidth: "95vw" };
        case "sm":
          return { width: "384px", maxWidth: "95vw" };
        case "md":
          return { width: "512px", maxWidth: "95vw" };
        case "lg":
          return { width: "720px", maxWidth: "95vw" };
        case "xl":
          return { width: "920px", maxWidth: "95vw" };
        case "full":
          return { width: "100vw", height: "100vh", maxWidth: "100vw" };
        default:
          return { width: "512px", maxWidth: "95vw" };
      }
    };

    const getModalPlacement = () => {
      if (variant === "drawer") {
        return placement || "right";
      }

      if (variant === "sheet") {
        return "bottom";
      }

      if (variant === "popup") {
        return "center";
      }

      return placement;
    };

    // Context value for multi-step forms
    const modalContextValue: ModalContextValue = {
      currentStep,
      totalSteps: steps.length,
      goToStep,
      nextStep,
      prevStep,
      isLastStep: currentStep === steps.length - 1,
      isFirstStep: currentStep === 0,
      closeModal: onClose,
      modalState,
      setModalState,
    };

    // Pre-compute colors for modal components to avoid conditional hook calls
    const modalBgColor = useColorModeValue("white", "gray.800");
    const borderColor = useColorModeValue("gray.200", "gray.700");
    const handleColor = useColorModeValue("gray.300", "gray.600");
    const resizeHandleColor = useColorModeValue("gray.400", "gray.500");
    const sheetHandleColor = useColorModeValue("gray.300", "gray.600");

    // Render specialized modal content
    const renderSpecializedContent = () => {
      if (isConfirmationModal) {
        return (
          <ConfirmationContent
            type={confirmationType}
            message={confirmationMessage}
          />
        );
      }

      if (isWalletModal && wallets.length > 0) {
        return <WalletConnectionContent wallets={wallets} />;
      }

      if (isTransactionModal && transaction) {
        return <TransactionConfirmationContent transaction={transaction} />;
      }

      if (isSwapSettingsModal && swapSettings && onSwapSettingsChange) {
        return (
          <SwapSettingsContent
            settings={swapSettings}
            onChange={onSwapSettingsChange}
          />
        );
      }

      if (steps.length > 0) {
        return (
          <>
            {showStepIndicator && (
              <StepIndicator
                steps={steps}
                currentStep={currentStep}
                onClick={goToStep}
              />
            )}

            <AnimatePresence mode="wait">
              <MotionBox
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                {steps[currentStep]?.content}
              </MotionBox>
            </AnimatePresence>
          </>
        );
      }

      if (sections.length > 0) {
        return (
          <VStack spacing={4} align="stretch">
            {sections.map((section) => (
              <CollapsibleSection key={section.id} section={section} />
            ))}
          </VStack>
        );
      }

      return children;
    };

    // Render drawer variant
    if (variant === "drawer") {
      const drawerPlacement = getModalPlacement() as
        | "top"
        | "right"
        | "bottom"
        | "left";
      const { width, height } = getModalSize();

      return (
        <AnimatePresence>
          {isOpen && (
            <Portal>
              <ModalContext.Provider value={modalContextValue}>
                <EnhancedBackdrop
                  onClick={handleOverlayClick}
                  isOpen={isOpen}
                  overlayColor={overlayColor}
                  overlayOpacity={overlayOpacity}
                  overlayBlur={overlayBlur}
                />

                <MotionDrawerContent
                  ref={combinedRef}
                  position="fixed"
                  top={drawerPlacement === "top" ? 0 : undefined}
                  right={drawerPlacement === "right" ? 0 : undefined}
                  bottom={drawerPlacement === "bottom" ? 0 : undefined}
                  left={drawerPlacement === "left" ? 0 : undefined}
                  width={width}
                  height={height}
                  zIndex={zIndex || 1400}
                  bg={modalBgColor}
                  boxShadow="dark-lg"
                  variants={drawerVariants}
                  custom={drawerPlacement}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  transition={{
                    duration: animationDuration,
                    delay: animationDelay,
                  }}
                  onAnimationComplete={onAnimationComplete}
                  aria-modal="true"
                  aria-labelledby={`drawer-${id || "modal"}-title`}
                  aria-describedby={ariaDescribedBy}
                  role="dialog"
                  {...rest}
                >
                  {showCloseButton && (
                    <IconButton
                      aria-label="Close drawer"
                      icon={<FaTimes />}
                      size="md"
                      position="absolute"
                      top="8px"
                      right="8px"
                      zIndex={2}
                      onClick={handleClose}
                    />
                  )}

                  {showHeader && (title || subtitle) && (
                    <Flex
                      p={6}
                      pb={3}
                      borderBottomWidth={1}
                      borderColor={borderColor}
                      align="center"
                    >
                      {headerIcon && <Box mr={3}>{headerIcon}</Box>}
                      <Box flex="1">
                        {title && (
                          <Heading
                            size="md"
                            id={`drawer-${id || "modal"}-title`}
                          >
                            {title}
                          </Heading>
                        )}
                        {subtitle && (
                          <Text mt={1} color="gray.500">
                            {subtitle}
                          </Text>
                        )}
                      </Box>

                      {headerActions && (
                        <HStack spacing={2}>
                          {headerActions.map((action, index) => (
                            <Tooltip
                              key={index}
                              label={action.tooltip || action.label}
                            >
                              <IconButton
                                aria-label={action.label}
                                icon={
                                  action.icon ? <>{action.icon}</> : undefined
                                }
                                size="sm"
                                variant="ghost"
                                onClick={action.onClick}
                                isDisabled={action.isDisabled}
                              />
                            </Tooltip>
                          ))}
                        </HStack>
                      )}
                    </Flex>
                  )}

                  <Box p={6} flex="1" overflowY="auto">
                    {renderSpecializedContent()}
                  </Box>

                  {showFooter &&
                    (primaryAction || secondaryAction || additionalActions) && (
                      <Flex
                        p={6}
                        borderTopWidth={1}
                        borderColor={borderColor}
                        justify="flex-end"
                        align="center"
                        wrap="wrap"
                      >
                        {additionalActions && (
                          <Box flex="1">
                            <HStack spacing={2}>
                              {additionalActions.map((action, index) => (
                                <Tooltip
                                  key={index}
                                  label={action.tooltip || action.label}
                                >
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    leftIcon={
                                      action.icon ? (
                                        <>{action.icon}</>
                                      ) : undefined
                                    }
                                    onClick={action.onClick}
                                    isDisabled={action.isDisabled}
                                    isLoading={action.isLoading}
                                  >
                                    {action.label}
                                    {action.shortcut && (
                                      <Kbd ml={2} fontSize="xs">
                                        {action.shortcut}
                                      </Kbd>
                                    )}
                                  </Button>
                                </Tooltip>
                              ))}
                            </HStack>
                          </Box>
                        )}

                        <HStack spacing={3}>
                          {secondaryAction && (
                            <Button
                              variant={secondaryAction.variant || "outline"}
                              colorScheme={
                                secondaryAction.colorScheme || "gray"
                              }
                              onClick={() => {
                                secondaryAction.onClick();
                                if (secondaryAction.closeOnClick) handleClose();
                              }}
                              isDisabled={secondaryAction.isDisabled}
                              isLoading={secondaryAction.isLoading}
                              leftIcon={
                                secondaryAction.icon ? (
                                  <>{secondaryAction.icon}</>
                                ) : undefined
                              }
                            >
                              {secondaryAction.label}
                              {secondaryAction.shortcut && (
                                <Kbd ml={2} fontSize="xs">
                                  {secondaryAction.shortcut}
                                </Kbd>
                              )}
                            </Button>
                          )}

                          {primaryAction && (
                            <Button
                              variant={primaryAction.variant || "solid"}
                              colorScheme={primaryAction.colorScheme || "blue"}
                              onClick={() => {
                                primaryAction.onClick();
                                if (primaryAction.closeOnClick) handleClose();
                              }}
                              isDisabled={primaryAction.isDisabled}
                              isLoading={primaryAction.isLoading}
                              leftIcon={
                                primaryAction.icon ? (
                                  <>{primaryAction.icon}</>
                                ) : undefined
                              }
                            >
                              {primaryAction.label}
                              {primaryAction.shortcut && (
                                <Kbd ml={2} fontSize="xs">
                                  {primaryAction.shortcut}
                                </Kbd>
                              )}
                            </Button>
                          )}
                        </HStack>
                      </Flex>
                    )}

                  {/* Keyboard shortcuts help */}
                  {Object.keys(shortcuts).length > 0 && (
                    <KeyboardShortcutsHelp
                      shortcuts={shortcuts}
                      isOpen={showKeyboardHelp}
                      onClose={() => setShowKeyboardHelp(false)}
                    />
                  )}

                  {/* Screen reader announcements */}
                  <VisuallyHidden>
                    <div aria-live="polite">
                      {modalState === "loading"
                        ? "Loading..."
                        : modalState === "success"
                        ? "Operation completed successfully"
                        : modalState === "error"
                        ? "An error occurred"
                        : ""}
                    </div>
                  </VisuallyHidden>
                </MotionDrawerContent>
              </ModalContext.Provider>
            </Portal>
          )}
        </AnimatePresence>
      );
    }

    // Render sheet variant
    if (variant === "sheet") {
      const { width, height } = getModalSize();

      return (
        <AnimatePresence>
          {isOpen && (
            <Portal>
              <ModalContext.Provider value={modalContextValue}>
                <EnhancedBackdrop
                  onClick={handleOverlayClick}
                  isOpen={isOpen}
                  overlayColor={overlayColor}
                  overlayOpacity={overlayOpacity}
                  overlayBlur={overlayBlur}
                />

                <MotionBox
                  ref={combinedRef}
                  position="fixed"
                  bottom={0}
                  left={0}
                  right={0}
                  height={height}
                  zIndex={zIndex || 1400}
                  bg={modalBgColor}
                  borderTopRadius="lg"
                  boxShadow="dark-lg"
                  variants={sheetVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  transition={{
                    duration: animationDuration,
                    delay: animationDelay,
                  }}
                  onAnimationComplete={onAnimationComplete}
                  aria-modal="true"
                  aria-labelledby={`sheet-${id || "modal"}-title`}
                  aria-describedby={ariaDescribedBy}
                  role="dialog"
                  {...rest}
                >
                  {/* Sheet handle */}
                  <Flex justify="center" pt={2} pb={1}>
                    <Box
                      width="40px"
                      height="5px"
                      borderRadius="full"
                      bg={sheetHandleColor}
                    />
                  </Flex>

                  {showCloseButton && (
                    <IconButton
                      aria-label="Close sheet"
                      icon={<FaTimes />}
                      size="md"
                      position="absolute"
                      top="8px"
                      right="8px"
                      zIndex={2}
                      onClick={handleClose}
                    />
                  )}

                  {showHeader && (title || subtitle) && (
                    <Flex
                      p={6}
                      pb={3}
                      borderBottomWidth={1}
                      borderColor={borderColor}
                      align="center"
                    >
                      {headerIcon && <Box mr={3}>{headerIcon}</Box>}
                      <Box flex="1">
                        {title && (
                          <Heading
                            size="md"
                            id={`sheet-${id || "modal"}-title`}
                          >
                            {title}
                          </Heading>
                        )}
                        {subtitle && (
                          <Text mt={1} color="gray.500">
                            {subtitle}
                          </Text>
                        )}
                      </Box>

                      {headerActions && (
                        <HStack spacing={2}>
                          {headerActions.map((action, index) => (
                            <Tooltip
                              key={index}
                              label={action.tooltip || action.label}
                            >
                              <IconButton
                                aria-label={action.label}
                                icon={
                                  action.icon ? <>{action.icon}</> : undefined
                                }
                                size="sm"
                                variant="ghost"
                                onClick={action.onClick}
                                isDisabled={action.isDisabled}
                              />
                            </Tooltip>
                          ))}
                        </HStack>
                      )}
                    </Flex>
                  )}

                  <Box p={6} flex="1" overflowY="auto">
                    {renderSpecializedContent()}
                  </Box>

                  {showFooter &&
                    (primaryAction || secondaryAction || additionalActions) && (
                      <Flex
                        p={6}
                        borderTopWidth={1}
                        borderColor={borderColor}
                        justify="flex-end"
                        align="center"
                        wrap="wrap"
                      >
                        {additionalActions && (
                          <Box flex="1">
                            <HStack spacing={2}>
                              {additionalActions.map((action, index) => (
                                <Tooltip
                                  key={index}
                                  label={action.tooltip || action.label}
                                >
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    leftIcon={
                                      action.icon ? (
                                        <>{action.icon}</>
                                      ) : undefined
                                    }
                                    onClick={action.onClick}
                                    isDisabled={action.isDisabled}
                                    isLoading={action.isLoading}
                                  >
                                    {action.label}
                                    {action.shortcut && (
                                      <Kbd ml={2} fontSize="xs">
                                        {action.shortcut}
                                      </Kbd>
                                    )}
                                  </Button>
                                </Tooltip>
                              ))}
                            </HStack>
                          </Box>
                        )}

                        <HStack spacing={3}>
                          {secondaryAction && (
                            <Button
                              variant={secondaryAction.variant || "outline"}
                              colorScheme={
                                secondaryAction.colorScheme || "gray"
                              }
                              onClick={() => {
                                secondaryAction.onClick();
                                if (secondaryAction.closeOnClick) handleClose();
                              }}
                              isDisabled={secondaryAction.isDisabled}
                              isLoading={secondaryAction.isLoading}
                              leftIcon={
                                secondaryAction.icon ? (
                                  <>{secondaryAction.icon}</>
                                ) : undefined
                              }
                            >
                              {secondaryAction.label}
                              {secondaryAction.shortcut && (
                                <Kbd ml={2} fontSize="xs">
                                  {secondaryAction.shortcut}
                                </Kbd>
                              )}
                            </Button>
                          )}

                          {primaryAction && (
                            <Button
                              variant={primaryAction.variant || "solid"}
                              colorScheme={primaryAction.colorScheme || "blue"}
                              onClick={() => {
                                primaryAction.onClick();
                                if (primaryAction.closeOnClick) handleClose();
                              }}
                              isDisabled={primaryAction.isDisabled}
                              isLoading={primaryAction.isLoading}
                              leftIcon={
                                primaryAction.icon ? (
                                  <>{primaryAction.icon}</>
                                ) : undefined
                              }
                            >
                              {primaryAction.label}
                              {primaryAction.shortcut && (
                                <Kbd ml={2} fontSize="xs">
                                  {primaryAction.shortcut}
                                </Kbd>
                              )}
                            </Button>
                          )}
                        </HStack>
                      </Flex>
                    )}

                  {/* Keyboard shortcuts help */}
                  {Object.keys(shortcuts).length > 0 && (
                    <KeyboardShortcutsHelp
                      shortcuts={shortcuts}
                      isOpen={showKeyboardHelp}
                      onClose={() => setShowKeyboardHelp(false)}
                    />
                  )}
                </MotionBox>
              </ModalContext.Provider>
            </Portal>
          )}
        </AnimatePresence>
      );
    }

    // Render standard modal variants (default, centered, full, popup)
    return (
      <AnimatePresence>
        {isOpen && (
          <Portal>
            <ModalContext.Provider value={modalContextValue}>
              <EnhancedBackdrop
                onClick={handleOverlayClick}
                isOpen={isOpen}
                overlayColor={overlayColor}
                overlayOpacity={overlayOpacity}
                overlayBlur={overlayBlur}
              />

              <RemoveScroll>
                <FocusScope contain restoreFocus autoFocus>
                  <MotionBox
                    ref={combinedRef}
                    position="fixed"
                    top={variant === "full" ? 0 : undefined}
                    left={variant === "full" ? 0 : undefined}
                    right={variant === "full" ? 0 : undefined}
                    bottom={variant === "full" ? 0 : undefined}
                    zIndex={zIndex || 1400}
                    display="flex"
                    alignItems={variant === "full" ? "flex-start" : "center"}
                    justifyContent="center"
                    width="100%"
                    height="100%"
                    pointerEvents="none"
                  >
                    <MotionBox
                      {...getModalSize()}
                      bg={modalBgColor}
                      borderRadius={variant === "full" ? 0 : "md"}
                      boxShadow="xl"
                      pointerEvents="auto"
                      variants={getModalVariant()}
                      custom={getModalPlacement()}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      transition={{
                        duration: animationDuration,
                        delay: animationDelay,
                      }}
                      onAnimationComplete={onAnimationComplete}
                      drag={isDraggable}
                      dragControls={dragControls}
                      dragListener={false}
                      dragConstraints={{
                        left: -300,
                        right: 300,
                        top: -200,
                        bottom: 200,
                      }}
                      dragElastic={0.1}
                      dragMomentum={false}
                      onDragEnd={(_, info) => handleDragEnd(info)}
                      style={
                        isDraggable
                          ? { x: position.x, y: position.y }
                          : undefined
                      }
                      aria-modal="true"
                      aria-labelledby={`modal-${id || "modal"}-title`}
                      aria-describedby={ariaDescribedBy}
                      role="dialog"
                      {...rest}
                    >
                      {/* Drag handle */}
                      {isDraggable && (
                        <Flex
                          position="absolute"
                          top="0"
                          left="0"
                          right="0"
                          height="10px"
                          justify="center"
                          align="center"
                          cursor="grab"
                          onPointerDown={handleDragStart}
                          _active={{ cursor: "grabbing" }}
                        >
                          <Box
                            width="40px"
                            height="4px"
                            borderRadius="full"
                            bg={handleColor}
                            mt={2}
                          />
                        </Flex>
                      )}

                      {/* Resize handle */}
                      {isResizable && (
                        <Box
                          position="absolute"
                          bottom="0"
                          right="0"
                          width="20px"
                          height="20px"
                          cursor="nwse-resize"
                          zIndex={2}
                          // In a real implementation, you would add resize logic here
                        >
                          <Box
                            position="absolute"
                            bottom="4px"
                            right="4px"
                            width="10px"
                            height="2px"
                            bg={resizeHandleColor}
                            transform="rotate(-45deg)"
                          />
                          <Box
                            position="absolute"
                            bottom="8px"
                            right="8px"
                            width="10px"
                            height="2px"
                            bg={resizeHandleColor}
                            transform="rotate(-45deg)"
                          />
                        </Box>
                      )}

                      {showCloseButton && (
                        <IconButton
                          aria-label="Close modal"
                          icon={<FaTimes />}
                          size="md"
                          position="absolute"
                          top="8px"
                          right="8px"
                          zIndex={2}
                          onClick={handleClose}
                        />
                      )}

                      {showHeader && (title || subtitle) && (
                        <Flex
                          p={6}
                          pb={3}
                          borderBottomWidth={1}
                          borderColor={borderColor}
                          align="center"
                        >
                          {headerIcon && <Box mr={3}>{headerIcon}</Box>}
                          <Box flex="1">
                            {title && (
                              <Heading
                                size="md"
                                id={`modal-${id || "modal"}-title`}
                              >
                                {title}
                              </Heading>
                            )}
                            {subtitle && (
                              <Text mt={1} color="gray.500">
                                {subtitle}
                              </Text>
                            )}
                          </Box>

                          {headerActions && (
                            <HStack spacing={2}>
                              {headerActions.map((action, index) => (
                                <Tooltip
                                  key={index}
                                  label={action.tooltip || action.label}
                                >
                                  <IconButton
                                    aria-label={action.label}
                                    icon={
                                      action.icon ? (
                                        <>{action.icon}</>
                                      ) : undefined
                                    }
                                    size="sm"
                                    variant="ghost"
                                    onClick={action.onClick}
                                    isDisabled={action.isDisabled}
                                  />
                                </Tooltip>
                              ))}
                            </HStack>
                          )}
                        </Flex>
                      )}

                      <Box p={6} flex="1" overflowY="auto">
                        {renderSpecializedContent()}
                      </Box>

                      {showFooter &&
                        (primaryAction ||
                          secondaryAction ||
                          additionalActions) && (
                          <Flex
                            p={6}
                            borderTopWidth={1}
                            borderColor={borderColor}
                            justify="flex-end"
                            align="center"
                            wrap="wrap"
                          >
                            {additionalActions && (
                              <Box flex="1">
                                <HStack spacing={2}>
                                  {additionalActions.map((action, index) => (
                                    <Tooltip
                                      key={index}
                                      label={action.tooltip || action.label}
                                    >
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        leftIcon={
                                          action.icon ? (
                                            <>{action.icon}</>
                                          ) : undefined
                                        }
                                        onClick={action.onClick}
                                        isDisabled={action.isDisabled}
                                        isLoading={action.isLoading}
                                      >
                                        {action.label}
                                        {action.shortcut && (
                                          <Kbd ml={2} fontSize="xs">
                                            {action.shortcut}
                                          </Kbd>
                                        )}
                                      </Button>
                                    </Tooltip>
                                  ))}
                                </HStack>
                              </Box>
                            )}

                            <HStack spacing={3}>
                              {secondaryAction && (
                                <Button
                                  variant={secondaryAction.variant || "outline"}
                                  colorScheme={
                                    secondaryAction.colorScheme || "gray"
                                  }
                                  onClick={() => {
                                    secondaryAction.onClick();
                                    if (secondaryAction.closeOnClick)
                                      handleClose();
                                  }}
                                  isDisabled={secondaryAction.isDisabled}
                                  isLoading={secondaryAction.isLoading}
                                  leftIcon={
                                    secondaryAction.icon ? (
                                      <>{secondaryAction.icon}</>
                                    ) : undefined
                                  }
                                >
                                  {secondaryAction.label}
                                  {secondaryAction.shortcut && (
                                    <Kbd ml={2} fontSize="xs">
                                      {secondaryAction.shortcut}
                                    </Kbd>
                                  )}
                                </Button>
                              )}

                              {primaryAction && (
                                <Button
                                  variant={primaryAction.variant || "solid"}
                                  colorScheme={
                                    primaryAction.colorScheme || "blue"
                                  }
                                  onClick={() => {
                                    primaryAction.onClick();
                                    if (primaryAction.closeOnClick)
                                      handleClose();
                                  }}
                                  isDisabled={primaryAction.isDisabled}
                                  isLoading={primaryAction.isLoading}
                                  leftIcon={
                                    primaryAction.icon ? (
                                      <>{primaryAction.icon}</>
                                    ) : undefined
                                  }
                                >
                                  {primaryAction.label}
                                  {primaryAction.shortcut && (
                                    <Kbd ml={2} fontSize="xs">
                                      {primaryAction.shortcut}
                                    </Kbd>
                                  )}
                                </Button>
                              )}
                            </HStack>
                          </Flex>
                        )}

                      {/* Keyboard shortcuts help */}
                      {Object.keys(shortcuts).length > 0 && (
                        <KeyboardShortcutsHelp
                          shortcuts={shortcuts}
                          isOpen={showKeyboardHelp}
                          onClose={() => setShowKeyboardHelp(false)}
                        />
                      )}

                      {/* Screen reader announcements */}
                      <VisuallyHidden>
                        <div aria-live="polite">
                          {modalState === "loading"
                            ? "Loading..."
                            : modalState === "success"
                            ? "Operation completed successfully"
                            : modalState === "error"
                            ? "An error occurred"
                            : ""}
                        </div>
                      </VisuallyHidden>
                    </MotionBox>
                  </MotionBox>
                </FocusScope>
              </RemoveScroll>
            </ModalContext.Provider>
          </Portal>
        )}
      </AnimatePresence>
    );
  }
);

EnhancedModal.displayName = "EnhancedModal";

// Export hook
export const useModal = () => useModalContext();

export default EnhancedModal;
