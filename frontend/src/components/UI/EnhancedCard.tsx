import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Flex,
  Text,
  Heading,
  Stack,
  HStack,
  VStack,
  Divider,
  Button,
  IconButton,
  Avatar,
  Badge,
  Skeleton,
  SkeletonText,
  SkeletonCircle,
  Icon /* Added */,
  useColorModeValue,
  useTheme,
  useDisclosure,
  Collapse,
  Tooltip,
  Tag,
  TagLabel,
  TagLeftIcon,
  Spacer,
  chakra,
  ThemingProps,
  SystemProps,
  ResponsiveValue,
  useMultiStyleConfig,
  StylesProvider,
  useStyles,
} from "@chakra-ui/react";
import {
  motion,
  AnimatePresence,
  useAnimation,
  Variants,
  useDragControls,
  PanInfo,
} from "framer-motion";
import {
  FaChevronDown,
  FaChevronUp,
  FaEllipsisH,
  FaExclamationCircle,
  FaCheckCircle,
  FaInfoCircle,
  FaBell,
  FaExchangeAlt,
  FaArrowUp,
  FaArrowDown,
  FaArrowRight /* Added */,
  FaGripVertical,
  FaEthereum,
  FaBitcoin,
  FaWallet,
  FaChartLine,
  FaLock,
  FaUnlock,
  FaExclamationTriangle,
  FaTimes,
} from "react-icons/fa";
import { transparentize, darken, lighten } from "@chakra-ui/theme-tools";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
} from "recharts";

// ========== Types & Interfaces ==========

export type CardVariant =
  | "default"
  | "elevated"
  | "flat"
  | "outlined"
  | "glass"
  | "gradient";

export type CardSize = "sm" | "md" | "lg" | "xl" | "full";

export type CardState = "idle" | "hover" | "active" | "loading" | "disabled";

export type NotificationType = "info" | "success" | "warning" | "error";

export type TransactionType =
  | "send"
  | "receive"
  | "swap"
  | "bridge"
  | "stake"
  | "unstake"
  | "approve";

export type TransactionStatus =
  | "pending"
  | "confirmed"
  | "failed"
  | "cancelled";

export type TrendDirection = "up" | "down" | "neutral";

export interface ChainInfo {
  id: number;
  name: string;
  icon?: React.ReactNode;
  color?: string;
}

export interface TokenInfo {
  symbol: string;
  name: string;
  icon?: string | React.ReactNode;
  balance?: string;
  value?: string;
  price?: string;
  priceChange?: {
    value: number;
    direction: TrendDirection;
  };
  chartData?: Array<{ time: string | number; value: number }>;
}

export interface TransactionInfo {
  hash: string;
  type: TransactionType;
  status: TransactionStatus;
  timestamp: string | number;
  fromChain?: ChainInfo;
  toChain?: ChainInfo;
  token?: TokenInfo;
  amount?: string;
  fee?: string;
}

export interface StatInfo {
  title: string;
  value: string | number;
  previousValue?: string | number;
  change?: {
    value: number;
    direction: TrendDirection;
  };
  icon?: React.ReactNode;
  formatter?: (value: string | number) => string;
}

export interface NotificationInfo {
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string | number;
  isRead?: boolean;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface CardAction {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: string;
  isDisabled?: boolean;
  isLoading?: boolean;
  tooltip?: string;
}

export interface EnhancedCardProps {
  // Base props
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;

  // Styling props
  variant?: CardVariant;
  size?: CardSize;
  state?: CardState;
  borderRadius?: ResponsiveValue<string | number>;
  boxShadow?: ResponsiveValue<string>;

  // Interactive props
  isInteractive?: boolean;
  isCollapsible?: boolean;
  isDraggable?: boolean;
  isInitiallyExpanded?: boolean;
  onClick?: () => void;

  // Visual effects
  glassMorphism?: boolean;
  glassMorphismStrength?: number;
  gradientFrom?: string;
  gradientTo?: string;
  gradientDirection?: string;

  // Header props
  avatar?: React.ReactNode;
  headerActions?: CardAction[];
  headerIcon?: React.ReactNode;
  headerBgColor?: string;

  // Footer props
  footerActions?: CardAction[];
  footerBgColor?: string;

  // Special card types
  portfolioToken?: TokenInfo;
  transaction?: TransactionInfo;
  notification?: NotificationInfo;
  stat?: StatInfo;

  // Animation props
  animateEntry?: boolean;
  animateExit?: boolean;
  animationDelay?: number;
  disableAnimation?: boolean;

  // Accessibility
  ariaLabel?: string;

  // Misc
  isFullWidth?: boolean;
  maxHeight?: ResponsiveValue<string | number>;
  maxWidth?: ResponsiveValue<string | number>;
  minHeight?: ResponsiveValue<string | number>;
  minWidth?: ResponsiveValue<string | number>;

  // Callbacks
  onDragEnd?: (info: PanInfo) => void;
  onExpand?: () => void;
  onCollapse?: () => void;

  // Additional props
  [key: string]: any;
}

// ========== Animation Variants ==========

const cardAnimationVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: {
      duration: 0.2,
      ease: "easeIn",
    },
  },
  hover: {
    y: -5,
    boxShadow: "0 8px 30px rgba(0, 0, 0, 0.12)",
    transition: {
      duration: 0.2,
      ease: "easeOut",
    },
  },
  tap: {
    scale: 0.98,
    transition: {
      duration: 0.1,
      ease: "easeOut",
    },
  },
  disabled: {
    opacity: 0.6,
    filter: "grayscale(30%)",
  },
};

const collapseIconVariants: Variants = {
  collapsed: { rotate: 0 },
  expanded: { rotate: 180 },
};

const valueChangeVariants: Variants = {
  initial: { opacity: 0, y: -10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  exit: { opacity: 0, y: 10, transition: { duration: 0.2 } },
};

const pulseVariants: Variants = {
  pulse: {
    scale: [1, 1.02, 1],
    opacity: [0.8, 1, 0.8],
    transition: { repeat: Infinity, duration: 2 },
  },
};

// ========== Helper Components ==========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);
const MotionHeading = motion(Heading);

// Animated counter for stat cards
const AnimatedCounter: React.FC<{
  value: number;
  duration?: number;
  formatter?: (value: number) => string;
}> = ({ value, duration = 1, formatter = (val) => val.toString() }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const prevValue = useRef(0);

  useEffect(() => {
    const start = prevValue.current;
    const end = value;
    const difference = end - start;
    const startTime = performance.now();

    const updateValue = () => {
      const now = performance.now();
      const elapsed = Math.min((now - startTime) / (duration * 1000), 1);
      const easedElapsed = easeOutQuart(elapsed);
      const currentValue = start + difference * easedElapsed;

      setDisplayValue(currentValue);

      if (elapsed < 1) {
        requestAnimationFrame(updateValue);
      } else {
        prevValue.current = end;
      }
    };

    requestAnimationFrame(updateValue);

    return () => {
      prevValue.current = value;
    };
  }, [value, duration]);

  // Easing function for smooth animation
  const easeOutQuart = (x: number): number => {
    return 1 - Math.pow(1 - x, 4);
  };

  return <>{formatter(displayValue)}</>;
};

// Trend indicator with animation
const TrendIndicator: React.FC<{
  direction: TrendDirection;
  value: number;
}> = ({ direction, value }) => {
  const upColor = useColorModeValue("green.500", "green.300");
  const downColor = useColorModeValue("red.500", "red.300");
  const neutralColor = useColorModeValue("gray.500", "gray.400");

  const getColor = () => {
    switch (direction) {
      case "up":
        return upColor;
      case "down":
        return downColor;
      default:
        return neutralColor;
    }
  };

  const getIcon = () => {
    switch (direction) {
      case "up":
        return FaArrowUp;
      case "down":
        return FaArrowDown;
      default:
        return null;
    }
  };

  const Icon = getIcon();

  return (
    <HStack spacing={1} color={getColor()}>
      {Icon && <Box as={Icon} />}
      <Text fontWeight="medium">
        {value > 0 && "+"}
        {value.toFixed(2)}%
      </Text>
    </HStack>
  );
};

// Mini chart for token cards
const MiniChart: React.FC<{
  data?: Array<{ time: string | number; value: number }>;
  trendDirection?: TrendDirection;
  height?: number;
  width?: number;
}> = ({ data = [], trendDirection = "neutral", height = 40, width = 100 }) => {
  const upColor = useColorModeValue("green.500", "green.300");
  const downColor = useColorModeValue("red.500", "red.300");
  const neutralColor = useColorModeValue("blue.500", "blue.300");

  const getColor = () => {
    switch (trendDirection) {
      case "up":
        return upColor;
      case "down":
        return downColor;
      default:
        return neutralColor;
    }
  };

  // If no data provided, generate sample data
  const chartData =
    data.length > 0
      ? data
      : Array.from({ length: 24 }, (_, i) => ({
          time: i,
          value:
            50 +
            Math.random() *
              50 *
              (trendDirection === "up"
                ? 1
                : trendDirection === "down"
                ? -1
                : i % 2 === 0
                ? 1
                : -1),
        }));

  return (
    <Box height={`${height}px`} width={`${width}px`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id={`colorGradient-${trendDirection}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="5%" stopColor={getColor()} stopOpacity={0.3} />
              <stop offset="95%" stopColor={getColor()} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={getColor()}
            strokeWidth={2}
            fillOpacity={1}
            fill={`url(#colorGradient-${trendDirection})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
};

// Transaction status badge
const TransactionStatusBadge: React.FC<{ status: TransactionStatus }> = ({
  status,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case "pending":
        return "yellow";
      case "confirmed":
        return "green";
      case "failed":
        return "red";
      case "cancelled":
        return "gray";
      default:
        return "gray";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "pending":
        return FaExchangeAlt;
      case "confirmed":
        return FaCheckCircle;
      case "failed":
        return FaExclamationCircle;
      case "cancelled":
        return FaTimes;
      default:
        return FaInfoCircle;
    }
  };

  return (
    <Badge
      colorScheme={getStatusColor()}
      variant="subtle"
      display="flex"
      alignItems="center"
    >
      <Box as={getStatusIcon()} mr={1} fontSize="xs" />
      <Text textTransform="capitalize">{status}</Text>
    </Badge>
  );
};

// Transaction type badge
const TransactionTypeBadge: React.FC<{ type: TransactionType }> = ({
  type,
}) => {
  const getTypeColor = () => {
    switch (type) {
      case "send":
        return "red";
      case "receive":
        return "green";
      case "swap":
        return "blue";
      case "bridge":
        return "purple";
      case "stake":
        return "teal";
      case "unstake":
        return "orange";
      case "approve":
        return "gray";
      default:
        return "gray";
    }
  };

  const getTypeIcon = () => {
    switch (type) {
      case "send":
        return FaArrowUp;
      case "receive":
        return FaArrowDown;
      case "swap":
        return FaExchangeAlt;
      case "bridge":
        return FaExchangeAlt;
      case "stake":
        return FaLock;
      case "unstake":
        return FaUnlock;
      case "approve":
        return FaCheckCircle;
      default:
        return FaInfoCircle;
    }
  };

  return (
    <Tag colorScheme={getTypeColor()} size="sm" borderRadius="full">
      <TagLeftIcon as={getTypeIcon()} />
      <TagLabel textTransform="capitalize">{type}</TagLabel>
    </Tag>
  );
};

// Notification indicator
const NotificationIndicator: React.FC<{
  type: NotificationType;
  isRead?: boolean;
}> = ({ type, isRead = false }) => {
  const getTypeColor = () => {
    switch (type) {
      case "info":
        return "blue";
      case "success":
        return "green";
      case "warning":
        return "yellow";
      case "error":
        return "red";
      default:
        return "blue";
    }
  };

  const getTypeIcon = () => {
    switch (type) {
      case "info":
        return FaInfoCircle;
      case "success":
        return FaCheckCircle;
      case "warning":
        return FaExclamationTriangle;
      case "error":
        return FaExclamationCircle;
      default:
        return FaInfoCircle;
    }
  };

  return (
    <Box position="relative">
      <Icon
        as={getTypeIcon()}
        color={`${getTypeColor()}.500`}
        boxSize={6}
        opacity={isRead ? 0.6 : 1}
      />
      {!isRead && (
        <Box
          position="absolute"
          top="-2px"
          right="-2px"
          width="8px"
          height="8px"
          borderRadius="full"
          bg="red.500"
        />
      )}
    </Box>
  );
};

// Card skeleton for loading state
const CardSkeleton: React.FC<{ size?: CardSize }> = ({ size = "md" }) => {
  const getSkeletonHeight = () => {
    switch (size) {
      case "sm":
        return "120px";
      case "md":
        return "200px";
      case "lg":
        return "300px";
      case "xl":
        return "400px";
      case "full":
        return "200px";
      default:
        return "200px";
    }
  };

  return (
    <Box
      padding="4"
      boxShadow="lg"
      bg="white"
      borderRadius="md"
      height={getSkeletonHeight()}
    >
      <SkeletonCircle size="10" />
      <SkeletonText mt="4" noOfLines={4} spacing="4" />
      <Skeleton height="20px" mt="4" />
    </Box>
  );
};

// ========== Specialized Card Components ==========

// Portfolio Token Card
const PortfolioTokenCard: React.FC<{ token: TokenInfo }> = ({ token }) => {
  const { symbol, name, icon, balance, value, price, priceChange, chartData } =
    token;

  return (
    <Box>
      <Flex align="center" justify="space-between" mb={4}>
        <HStack spacing={3}>
          {typeof icon === "string" ? (
            <Avatar size="sm" src={icon} name={symbol} />
          ) : icon ? (
            <Box>{icon}</Box>
          ) : (
            <Avatar size="sm" name={symbol} />
          )}
          <Box>
            <Heading size="sm">{symbol}</Heading>
            <Text fontSize="xs" color="gray.500">
              {name}
            </Text>
          </Box>
        </HStack>

        {priceChange && (
          <TrendIndicator
            direction={priceChange.direction}
            value={priceChange.value}
          />
        )}
      </Flex>

      <Flex justify="space-between" align="flex-end" mb={3}>
        <Box>
          <Text fontSize="xs" color="gray.500">
            Balance
          </Text>
          <Text fontWeight="bold">
            {balance} {symbol}
          </Text>
          {value && (
            <Text fontSize="sm" color="gray.500">
              ${value}
            </Text>
          )}
        </Box>

        <Box>
          <Text fontSize="xs" color="gray.500" textAlign="right">
            Price
          </Text>
          <Text fontWeight="bold" textAlign="right">
            ${price}
          </Text>
        </Box>
      </Flex>

      <MiniChart
        data={chartData}
        trendDirection={priceChange?.direction || "neutral"}
        height={60}
        width={240}
      />
    </Box>
  );
};

// Transaction Card
const TransactionCard: React.FC<{ transaction: TransactionInfo }> = ({
  transaction,
}) => {
  const {
    hash,
    type,
    status,
    timestamp,
    fromChain,
    toChain,
    token,
    amount,
    fee,
  } = transaction;

  const formattedHash = `${hash.slice(0, 6)}...${hash.slice(-4)}`;
  const formattedTime =
    typeof timestamp === "string"
      ? timestamp
      : new Date(timestamp).toLocaleString();

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={3}>
        <TransactionTypeBadge type={type} />
        <TransactionStatusBadge status={status} />
      </Flex>

      <Flex justify="space-between" mb={4}>
        <Text fontSize="sm" color="gray.500">
          Tx: {formattedHash}
        </Text>
        <Text fontSize="sm" color="gray.500">
          {formattedTime}
        </Text>
      </Flex>

      {(fromChain || toChain) && (
        <Flex align="center" mb={4}>
          {fromChain && (
            <HStack>
              {fromChain.icon || (
                <Box
                  boxSize={4}
                  borderRadius="full"
                  bg={fromChain.color || "gray.400"}
                />
              )}
              <Text fontSize="sm">{fromChain.name}</Text>
            </HStack>
          )}

          {fromChain && toChain && (
            <Box mx={2}>
              <FaArrowRight />
            </Box>
          )}

          {toChain && (
            <HStack>
              {toChain.icon || (
                <Box
                  boxSize={4}
                  borderRadius="full"
                  bg={toChain.color || "gray.400"}
                />
              )}
              <Text fontSize="sm">{toChain.name}</Text>
            </HStack>
          )}
        </Flex>
      )}

      {token && amount && (
        <Flex justify="space-between" mb={2}>
          <HStack>
            {typeof token.icon === "string" ? (
              <Avatar size="xs" src={token.icon} name={token.symbol} />
            ) : token.icon ? (
              <Box>{token.icon}</Box>
            ) : (
              <Avatar size="xs" name={token.symbol} />
            )}
            <Text>{token.symbol}</Text>
          </HStack>
          <Text fontWeight="bold">{amount}</Text>
        </Flex>
      )}

      {fee && (
        <Flex justify="space-between">
          <Text fontSize="sm" color="gray.500">
            Fee
          </Text>
          <Text fontSize="sm" color="gray.500">
            {fee}
          </Text>
        </Flex>
      )}
    </Box>
  );
};

// Notification Card
const NotificationCard: React.FC<{ notification: NotificationInfo }> = ({
  notification,
}) => {
  const {
    type,
    title,
    message,
    timestamp,
    isRead = false,
    icon,
    action,
  } = notification;

  const formattedTime =
    typeof timestamp === "string"
      ? timestamp
      : new Date(timestamp).toLocaleString();

  return (
    <Box opacity={isRead ? 0.7 : 1}>
      <Flex align="flex-start" mb={2}>
        <Box mr={3}>
          {icon || <NotificationIndicator type={type} isRead={isRead} />}
        </Box>

        <Box flex="1">
          <Flex justify="space-between" align="center" mb={1}>
            <Heading size="sm">{title}</Heading>
            <Text fontSize="xs" color="gray.500">
              {formattedTime}
            </Text>
          </Flex>

          <Text fontSize="sm" mb={action ? 3 : 0}>
            {message}
          </Text>

          {action && (
            <Button
              size="sm"
              variant="link"
              colorScheme="blue"
              onClick={action.onClick}
              mt={2}
            >
              {action.label}
            </Button>
          )}
        </Box>
      </Flex>
    </Box>
  );
};

// Stats Card
const StatsCard: React.FC<{ stat: StatInfo }> = ({ stat }) => {
  const {
    title,
    value,
    previousValue,
    change,
    icon,
    formatter = (val) => val.toString(),
  } = stat;

  const formattedValue = typeof value === "number" ? formatter(value) : value;

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={2}>
        <Text fontSize="sm" color="gray.500">
          {title}
        </Text>
        {icon && <Box>{icon}</Box>}
      </Flex>

      <Heading size="lg" mb={change ? 2 : 0}>
        {typeof value === "number" ? (
          <AnimatedCounter
            value={value as number}
            formatter={(val) => formatter(val)}
          />
        ) : (
          formattedValue
        )}
      </Heading>

      {change && (
        <TrendIndicator direction={change.direction} value={change.value} />
      )}
    </Box>
  );
};

// ========== Main Component ==========

export const EnhancedCard: React.FC<EnhancedCardProps> = ({
  // Base props
  title,
  subtitle,
  children,
  footer,

  // Styling props
  variant = "default",
  size = "md",
  state = "idle",
  borderRadius = "md",
  boxShadow,

  // Interactive props
  isInteractive = false,
  isCollapsible = false,
  isDraggable = false,
  isInitiallyExpanded = true,
  onClick,

  // Visual effects
  glassMorphism = false,
  glassMorphismStrength = 10,
  gradientFrom,
  gradientTo,
  gradientDirection = "to right",

  // Header props
  avatar,
  headerActions,
  headerIcon,
  headerBgColor,

  // Footer props
  footerActions,
  footerBgColor,

  // Special card types
  portfolioToken,
  transaction,
  notification,
  stat,

  // Animation props
  animateEntry = true,
  animateExit = true,
  animationDelay = 0,
  disableAnimation = false,

  // Accessibility
  ariaLabel,

  // Misc
  isFullWidth = false,
  maxHeight,
  maxWidth,
  minHeight,
  minWidth,

  // Callbacks
  onDragEnd,
  onExpand,
  onCollapse,

  // Additional props
  ...rest
}) => {
  // Hooks
  const { isOpen: isExpanded, onToggle } = useDisclosure({
    defaultIsOpen: isInitiallyExpanded,
  });
  const controls = useAnimation();
  const dragControls = useDragControls();
  const cardRef = useRef<HTMLDivElement>(null);

  // Theme values
  const theme = useTheme();
  const bgColor = useColorModeValue("white", "gray.800");
  const textColor = useColorModeValue("gray.800", "white");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  // Pre-compute default background colors to avoid conditional Hook calls
  const defaultHeaderBg = useColorModeValue("gray.50", "gray.900");
  const defaultFooterBg = useColorModeValue("gray.50", "gray.900");
  const headerBg = headerBgColor || defaultHeaderBg;
  const footerBg = footerBgColor || defaultFooterBg;
  // Pre-computed color for flat variant to avoid hook in nested fn
  const flatBgColor = useColorModeValue("gray.100", "gray.700");

  // Effects

  // Handle state changes
  useEffect(() => {
    if (state === "disabled") {
      controls.start("disabled");
    } else {
      controls.start("visible");
    }
  }, [state, controls]);

  // Handle collapse/expand
  useEffect(() => {
    if (onExpand && isExpanded) {
      onExpand();
    } else if (onCollapse && !isExpanded) {
      onCollapse();
    }
  }, [isExpanded, onExpand, onCollapse]);

  // Handlers
  const handleToggleCollapse = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggle();
  };

  const handleCardClick = () => {
    if (isInteractive && onClick && state !== "disabled") {
      onClick();
    }
  };

  const handleDragStart = (
    event: PointerEvent | React.PointerEvent<Element>
  ) => {
    if (isDraggable) {
      dragControls.start(event);
    }
  };

  // Determine card background based on variant and effects
  const getCardBackground = () => {
    if (glassMorphism) {
      return "rgba(255, 255, 255, 0.1)";
    }

    if (gradientFrom && gradientTo) {
      return `linear-gradient(${gradientDirection}, ${gradientFrom}, ${gradientTo})`;
    }

    switch (variant) {
      case "flat":
        return flatBgColor;
      case "glass":
        return "rgba(255, 255, 255, 0.1)";
      case "gradient":
        return "linear-gradient(to right, var(--chakra-colors-blue-500), var(--chakra-colors-purple-500))";
      default:
        return bgColor;
    }
  };

  // Determine card border based on variant
  const getCardBorder = () => {
    if (variant === "outlined") {
      return `1px solid ${borderColor}`;
    }

    if (glassMorphism) {
      return "1px solid rgba(255, 255, 255, 0.2)";
    }

    return "none";
  };

  // Determine card shadow based on variant
  const getCardShadow = () => {
    if (boxShadow) return boxShadow;

    switch (variant) {
      case "elevated":
        return "lg";
      case "default":
        return "md";
      case "glass":
        return "0 8px 32px rgba(0, 0, 0, 0.1)";
      default:
        return "none";
    }
  };

  // Determine card padding based on size
  const getCardPadding = () => {
    switch (size) {
      case "sm":
        return 3;
      case "md":
        return 4;
      case "lg":
        return 5;
      case "xl":
        return 6;
      default:
        return 4;
    }
  };

  // Determine card width based on size
  const getCardWidth = () => {
    if (isFullWidth) return "100%";

    switch (size) {
      case "sm":
        return "280px";
      case "md":
        return "320px";
      case "lg":
        return "380px";
      case "xl":
        return "480px";
      case "full":
        return "100%";
      default:
        return "320px";
    }
  };

  // Determine card text color based on variant
  const getCardTextColor = () => {
    if (variant === "gradient") {
      return "white";
    }

    return textColor;
  };

  // Render specialized card content based on props
  const renderSpecializedContent = () => {
    if (portfolioToken) {
      return <PortfolioTokenCard token={portfolioToken} />;
    }

    if (transaction) {
      return <TransactionCard transaction={transaction} />;
    }

    if (notification) {
      return <NotificationCard notification={notification} />;
    }

    if (stat) {
      return <StatsCard stat={stat} />;
    }

    return children;
  };

  // Loading state
  if (state === "loading") {
    return <CardSkeleton size={size} />;
  }

  // Main render
  return (
    <MotionBox
      ref={cardRef}
      width={getCardWidth()}
      bg={getCardBackground()}
      color={getCardTextColor()}
      borderRadius={borderRadius}
      boxShadow={getCardShadow()}
      border={getCardBorder()}
      overflow="hidden"
      position="relative"
      cursor={isInteractive ? "pointer" : "default"}
      onClick={handleCardClick}
      maxWidth={maxWidth}
      maxHeight={maxHeight}
      minWidth={minWidth}
      minHeight={minHeight}
      aria-label={ariaLabel || title}
      tabIndex={isInteractive ? 0 : undefined}
      role={isInteractive ? "button" : undefined}
      aria-expanded={isCollapsible ? isExpanded : undefined}
      variants={!disableAnimation ? cardAnimationVariants : undefined}
      initial={animateEntry ? "hidden" : "visible"}
      animate={controls}
      exit={animateExit ? "exit" : undefined}
      transition={{ delay: animationDelay }}
      whileHover={isInteractive && !disableAnimation ? "hover" : undefined}
      whileTap={isInteractive && !disableAnimation ? "tap" : undefined}
      drag={isDraggable ? true : undefined}
      dragControls={dragControls}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragElastic={0.1}
      dragTransition={{ bounceStiffness: 300, bounceDamping: 20 }}
      onDragEnd={(_, info) => onDragEnd && onDragEnd(info)}
      backdropFilter={
        glassMorphism ? `blur(${glassMorphismStrength}px)` : undefined
      }
      {...rest}
    >
      {/* Drag Handle */}
      {isDraggable && (
        <Flex
          position="absolute"
          top="0"
          left="0"
          right="0"
          justify="center"
          py={1}
          onPointerDown={handleDragStart}
          cursor="grab"
          _active={{ cursor: "grabbing" }}
          zIndex={2}
        >
          <Icon as={FaGripVertical} color="gray.400" />
        </Flex>
      )}

      {/* Card Header */}
      {(title ||
        subtitle ||
        avatar ||
        headerIcon ||
        headerActions ||
        isCollapsible) && (
        <Flex
          align="center"
          justify="space-between"
          p={getCardPadding()}
          pb={subtitle ? 2 : getCardPadding()}
          borderBottomWidth={subtitle ? 0 : 1}
          borderColor={borderColor}
          bg={headerBgColor}
        >
          <Flex align="center">
            {avatar && <Box mr={3}>{avatar}</Box>}
            {headerIcon && <Box mr={3}>{headerIcon}</Box>}

            <Box>
              {title && (
                <Heading size={size === "sm" ? "xs" : "md"}>{title}</Heading>
              )}
              {subtitle && (
                <Text color="gray.500" fontSize="sm">
                  {subtitle}
                </Text>
              )}
            </Box>
          </Flex>

          <HStack spacing={2}>
            {headerActions &&
              headerActions.map((action, index) => (
                <Tooltip
                  key={index}
                  label={action.tooltip}
                  isDisabled={!action.tooltip}
                >
                  <IconButton
                    aria-label={action.label}
                    icon={action.icon ? <>{action.icon}</> : undefined}
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      action.onClick();
                    }}
                    isDisabled={action.isDisabled}
                    isLoading={action.isLoading}
                  />
                </Tooltip>
              ))}

            {isCollapsible && (
              <IconButton
                aria-label={isExpanded ? "Collapse" : "Expand"}
                icon={<Icon as={isExpanded ? FaChevronUp : FaChevronDown} />}
                size="sm"
                variant="ghost"
                onClick={handleToggleCollapse}
              />
            )}
          </HStack>
        </Flex>
      )}

      {/* Subtitle (if separated from title) */}
      {title && subtitle && (
        <Box
          px={getCardPadding()}
          pb={3}
          pt={0}
          borderBottomWidth={1}
          borderColor={borderColor}
        >
          <Text color="gray.500" fontSize="sm">
            {subtitle}
          </Text>
        </Box>
      )}

      {/* Card Content */}
      <Collapse in={!isCollapsible || isExpanded} animateOpacity>
        <Box p={getCardPadding()}>{renderSpecializedContent()}</Box>
      </Collapse>

      {/* Card Footer */}
      {(footer || footerActions) && (
        <Box
          p={getCardPadding()}
          borderTopWidth={1}
          borderColor={borderColor}
          bg={footerBg}
        >
          {footer ? (
            footer
          ) : footerActions ? (
            <Flex justify="flex-end">
              <HStack spacing={2}>
                {footerActions.map((action, index) => (
                  <Button
                    key={index}
                    size="sm"
                    variant={action.variant || "ghost"}
                    leftIcon={action.icon ? <>{action.icon}</> : undefined}
                    onClick={(e) => {
                      e.stopPropagation();
                      action.onClick();
                    }}
                    isDisabled={action.isDisabled}
                    isLoading={action.isLoading}
                  >
                    {action.label}
                  </Button>
                ))}
              </HStack>
            </Flex>
          ) : null}
        </Box>
      )}

      {/* Glassmorphism Overlay */}
      {glassMorphism && (
        <Box
          position="absolute"
          top="0"
          left="0"
          right="0"
          bottom="0"
          backdropFilter={`blur(${glassMorphismStrength}px)`}
          borderRadius={borderRadius}
          zIndex="-1"
          pointerEvents="none"
        />
      )}
    </MotionBox>
  );
};

export default EnhancedCard;
