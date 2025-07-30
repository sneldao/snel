import React, { useState, useEffect } from "react";
import {
  Button as ChakraButton,
  ButtonProps as ChakraButtonProps,
  Box,
  Flex,
  Text,
  Spinner,
  useTheme,
  useColorModeValue,
  forwardRef,
  Tooltip,
  Progress,
  Icon,
  useStyleConfig,
  ThemingProps,
  SystemProps,
  ResponsiveValue,
  IconButton,
} from "@chakra-ui/react";
import { motion, AnimatePresence, useAnimation, Variants } from "framer-motion";
import {
  FaCheck,
  FaTimes,
  FaExclamationTriangle,
  FaWallet,
  FaLock,
  FaExchangeAlt,
  FaSignOutAlt,
  FaArrowRight,
  FaArrowLeft,
} from "react-icons/fa";
import { transparentize, darken, lighten } from "@chakra-ui/theme-tools";

// ========== Types & Interfaces ==========

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "outline"
  | "ghost"
  | "danger"
  | "success"
  | "wallet"
  | "transaction"
  | "gradient"
  | "glass";

export type ButtonSize = "xs" | "sm" | "md" | "lg" | "xl";

export type ButtonState =
  | "idle"
  | "loading"
  | "success"
  | "error"
  | "progress"
  | "confirming";

export type IconPosition = "left" | "right";

export interface EnhancedButtonProps
  extends Omit<ChakraButtonProps, "variant" | "size"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  state?: ButtonState;
  progress?: number;
  icon?: React.ReactElement;
  iconPosition?: IconPosition;
  iconSpacing?: SystemProps["mr"];
  endIcon?: React.ReactElement;
  loadingText?: string;
  successText?: string;
  errorText?: string;
  confirmingText?: string;
  soundEffect?: string;
  pulseAnimation?: boolean;
  pulseColor?: string;
  pulseIntensity?: number;
  glassMorphism?: boolean;
  gradientFrom?: string;
  gradientTo?: string;
  gradientDirection?: string;
  transactionHash?: string;
  chainIcon?: React.ReactElement;
  tooltipText?: string;
  disableAnimation?: boolean;
  fullWidth?: boolean;
  rounded?: ResponsiveValue<"sm" | "md" | "lg" | "xl" | "full">;
  textTransform?: SystemProps["textTransform"];
}

// ========== Animation Variants ==========

const buttonAnimationVariants: Variants = {
  idle: {
    scale: 1,
  },
  hover: {
    scale: 1.02,
    transition: { duration: 0.2 },
  },
  tap: {
    scale: 0.98,
    transition: { duration: 0.1 },
  },
  disabled: {
    opacity: 0.6,
    scale: 1,
  },
};

const pulseAnimationVariants: Variants = {
  pulse: {
    boxShadow: [
      "0 0 0 0 rgba(var(--pulse-color), 0.7)",
      "0 0 0 10px rgba(var(--pulse-color), 0)",
      "0 0 0 0 rgba(var(--pulse-color), 0)",
    ],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      repeatType: "loop",
    },
  },
};

const iconAnimationVariants: Variants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.2 } },
  exit: { opacity: 0, x: 10, transition: { duration: 0.2 } },
};

const successIconVariants: Variants = {
  hidden: { scale: 0, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 10,
    },
  },
};

// ========== Helper Components ==========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionChakraButton = motion(ChakraButton);

// ========== Helper Functions ==========

const getButtonStateIcon = (state: ButtonState) => {
  switch (state) {
    case "success":
      return <Icon as={FaCheck} />;
    case "error":
      return <Icon as={FaTimes} />;
    case "confirming":
      return <Icon as={FaExchangeAlt} />;
    default:
      return null;
  }
};

const getButtonStateText = (
  state: ButtonState,
  children: React.ReactNode,
  loadingText?: string,
  successText?: string,
  errorText?: string,
  confirmingText?: string
) => {
  switch (state) {
    case "loading":
      return loadingText || "Loading...";
    case "success":
      return successText || "Success!";
    case "error":
      return errorText || "Error!";
    case "confirming":
      return confirmingText || "Confirming...";
    default:
      return children;
  }
};

const hexToRgb = (hex: string) => {
  // Remove # if present
  hex = hex.replace("#", "");

  // Parse the hex values
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  return `${r}, ${g}, ${b}`;
};

// ========== Main Component ==========

export const EnhancedButton = forwardRef<EnhancedButtonProps, "button">(
  (props, ref) => {
    const {
      variant = "primary",
      size = "md",
      state = "idle",
      progress = 0,
      icon,
      iconPosition = "left",
      iconSpacing = 2,
      endIcon,
      loadingText,
      successText,
      errorText,
      confirmingText,
      soundEffect,
      pulseAnimation = false,
      pulseColor,
      pulseIntensity = 0.7,
      glassMorphism = false,
      gradientFrom,
      gradientTo,
      gradientDirection = "to right",
      transactionHash,
      chainIcon,
      tooltipText,
      disableAnimation = false,
      fullWidth = false,
      rounded = "md",
      textTransform,
      children,
      isDisabled,
      onClick,
      ...rest
    } = props;

    const theme = useTheme();
    const controls = useAnimation();
    const [isHovered, setIsHovered] = useState(false);
    const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(
      null
    );

    // Set up sound effect
    useEffect(() => {
      if (soundEffect) {
        const audio = new Audio(soundEffect);
        setAudioElement(audio);
        return () => {
          audio.pause();
          audio.currentTime = 0;
        };
      }
    }, [soundEffect]);

    // Handle button click with sound
    const handleClick = (
      e: React.MouseEvent<HTMLButtonElement, MouseEvent>
    ) => {
      if (audioElement && !isDisabled && state === "idle") {
        audioElement.currentTime = 0;
        audioElement
          .play()
          .catch((error) => console.error("Error playing sound:", error));
      }

      if (onClick && !isDisabled && state === "idle") {
        onClick(e);
      }
    };

    // Colors based on theme
    const primaryColor = useColorModeValue("blue.500", "blue.300");
    const secondaryColor = useColorModeValue("gray.600", "gray.400");
    const dangerColor = useColorModeValue("red.500", "red.300");
    const successColor = useColorModeValue("green.500", "green.300");
    const walletColor = useColorModeValue("purple.500", "purple.300");
    const transactionColor = useColorModeValue("orange.500", "orange.300");

    const bgColor = useColorModeValue("white", "gray.800");
    const textColor = useColorModeValue("gray.800", "white");
    const borderColor = useColorModeValue("gray.200", "gray.600");

    // Determine button background color based on variant
    const getButtonBgColor = () => {
      if (glassMorphism) {
        return "rgba(255, 255, 255, 0.1)";
      }

      if (gradientFrom && gradientTo) {
        return `linear-gradient(${gradientDirection}, ${gradientFrom}, ${gradientTo})`;
      }

      switch (variant) {
        case "primary":
          return primaryColor;
        case "secondary":
          return secondaryColor;
        case "outline":
        case "ghost":
          return "transparent";
        case "danger":
          return dangerColor;
        case "success":
          return successColor;
        case "wallet":
          return walletColor;
        case "transaction":
          return transactionColor;
        case "gradient":
          return "linear-gradient(to right, blue.400, purple.500)";
        case "glass":
          return "rgba(255, 255, 255, 0.1)";
        default:
          return primaryColor;
      }
    };

    // Determine button text color based on variant
    const getButtonTextColor = () => {
      switch (variant) {
        case "primary":
        case "secondary":
        case "danger":
        case "success":
        case "wallet":
        case "transaction":
        case "gradient":
          return "white";
        case "outline":
          return primaryColor;
        case "ghost":
          return textColor;
        case "glass":
          return "white";
        default:
          return "white";
      }
    };

    // Determine button border based on variant
    const getButtonBorder = () => {
      if (variant === "outline") {
        return `1px solid ${primaryColor}`;
      }

      if (glassMorphism) {
        return "1px solid rgba(255, 255, 255, 0.2)";
      }

      return "none";
    };

    // Determine button hover style based on variant
    const getButtonHoverStyle = () => {
      if (disableAnimation) return {};

      if (glassMorphism) {
        return {
          bg: "rgba(255, 255, 255, 0.2)",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
        };
      }

      if (gradientFrom && gradientTo) {
        return {
          opacity: 0.9,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
        };
      }

      switch (variant) {
        case "primary":
          return { bg: darken(primaryColor, 10) };
        case "secondary":
          return { bg: darken(secondaryColor, 10) };
        case "outline":
          return { bg: transparentize(primaryColor, 0.9) };
        case "ghost":
          return { bg: transparentize(primaryColor, 0.9) };
        case "danger":
          return { bg: darken(dangerColor, 10) };
        case "success":
          return { bg: darken(successColor, 10) };
        case "wallet":
          return { bg: darken(walletColor, 10) };
        case "transaction":
          return { bg: darken(transactionColor, 10) };
        case "gradient":
          return { opacity: 0.9 };
        case "glass":
          return { bg: "rgba(255, 255, 255, 0.2)" };
        default:
          return { bg: darken(primaryColor, 10) };
      }
    };

    // Calculate button padding based on size
    const getButtonPadding = () => {
      switch (size) {
        case "xs":
          return { px: 2, py: 1 };
        case "sm":
          return { px: 3, py: 1 };
        case "md":
          return { px: 4, py: 2 };
        case "lg":
          return { px: 6, py: 3 };
        case "xl":
          return { px: 8, py: 4 };
        default:
          return { px: 4, py: 2 };
      }
    };

    // Calculate font size based on size
    const getButtonFontSize = () => {
      switch (size) {
        case "xs":
          return "xs";
        case "sm":
          return "sm";
        case "md":
          return "md";
        case "lg":
          return "lg";
        case "xl":
          return "xl";
        default:
          return "md";
      }
    };

    // Calculate icon size based on button size
    const getIconSize = () => {
      switch (size) {
        case "xs":
          return "12px";
        case "sm":
          return "14px";
        case "md":
          return "16px";
        case "lg":
          return "20px";
        case "xl":
          return "24px";
        default:
          return "16px";
      }
    };

    // Handle button state changes
    useEffect(() => {
      if (isDisabled) {
        controls.start("disabled");
      } else {
        controls.start("idle");
      }
    }, [isDisabled, controls]);

    // Get pulse color in RGB format for CSS variable
    const getPulseColorRgb = () => {
      if (pulseColor) {
        return hexToRgb(pulseColor);
      }

      switch (variant) {
        case "primary":
          return hexToRgb(theme.colors.blue[500]);
        case "secondary":
          return hexToRgb(theme.colors.gray[500]);
        case "danger":
          return hexToRgb(theme.colors.red[500]);
        case "success":
          return hexToRgb(theme.colors.green[500]);
        case "wallet":
          return hexToRgb(theme.colors.purple[500]);
        case "transaction":
          return hexToRgb(theme.colors.orange[500]);
        default:
          return hexToRgb(theme.colors.blue[500]);
      }
    };

    // Generate button content based on state
    const renderButtonContent = () => {
      const displayText = getButtonStateText(
        state,
        children,
        loadingText,
        successText,
        errorText,
        confirmingText
      );

      const displayIcon = state !== "idle" ? getButtonStateIcon(state) : icon;
      const showEndIcon = state === "idle" && endIcon;

      return (
        <Flex align="center" justify="center" width="100%" position="relative">
          {/* Left Icon */}
          {displayIcon && iconPosition === "left" && (
            <AnimatePresence>
              <MotionBox
                display="flex"
                alignItems="center"
                mr={iconSpacing}
                variants={iconAnimationVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                {state === "loading" ? (
                  <Spinner
                    size={size === "xs" || size === "sm" ? "xs" : "sm"}
                  />
                ) : (
                  React.cloneElement(displayIcon as React.ReactElement, {
                    size: getIconSize(),
                  })
                )}
              </MotionBox>
            </AnimatePresence>
          )}

          {/* Text Content */}
          <AnimatePresence>
            <MotionBox
              textAlign="center"
              variants={
                state !== "idle" ? { visible: { opacity: 1 } } : undefined
              }
              initial={state !== "idle" ? { opacity: 0 } : undefined}
              animate={state !== "idle" ? "visible" : undefined}
              transition={{ duration: 0.2 }}
              textTransform={textTransform}
            >
              {displayText}
            </MotionBox>
          </AnimatePresence>

          {/* Right Icon or End Icon */}
          {((displayIcon && iconPosition === "right") || showEndIcon) && (
            <AnimatePresence>
              <MotionBox
                display="flex"
                alignItems="center"
                ml={iconSpacing}
                variants={iconAnimationVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                {state === "loading" ? (
                  <Spinner
                    size={size === "xs" || size === "sm" ? "xs" : "sm"}
                  />
                ) : iconPosition === "right" ? (
                  React.cloneElement(displayIcon as React.ReactElement, {
                    size: getIconSize(),
                  })
                ) : (
                  showEndIcon &&
                  React.cloneElement(endIcon as React.ReactElement, {
                    size: getIconSize(),
                  })
                )}
              </MotionBox>
            </AnimatePresence>
          )}

          {/* Progress Bar for 'progress' state */}
          {state === "progress" && (
            <Box
              position="absolute"
              bottom="0"
              left="0"
              width="100%"
              height="4px"
              overflow="hidden"
              borderBottomLeftRadius={rounded}
              borderBottomRightRadius={rounded}
            >
              <Progress
                value={progress}
                size="xs"
                colorScheme={
                  variant === "primary"
                    ? "blue"
                    : variant === "danger"
                    ? "red"
                    : variant === "success"
                    ? "green"
                    : variant === "wallet"
                    ? "purple"
                    : variant === "transaction"
                    ? "orange"
                    : "blue"
                }
                hasStripe
                isAnimated
              />
            </Box>
          )}
        </Flex>
      );
    };

    // Special button for wallet connection
    if (variant === "wallet") {
      return (
        <Tooltip label={tooltipText} isDisabled={!tooltipText}>
          <MotionChakraButton
            ref={ref}
            display="flex"
            alignItems="center"
            justifyContent="center"
            bg={getButtonBgColor()}
            color={getButtonTextColor()}
            border={getButtonBorder()}
            borderRadius={rounded}
            width={fullWidth ? "100%" : "auto"}
            {...getButtonPadding()}
            fontSize={getButtonFontSize()}
            isDisabled={isDisabled || state === "loading"}
            onClick={handleClick}
            _hover={!isDisabled ? getButtonHoverStyle() : undefined}
            _active={!isDisabled ? { transform: "scale(0.98)" } : undefined}
            position="relative"
            overflow="hidden"
            transition="all 0.2s"
            whileHover={!disableAnimation && !isDisabled ? { scale: 1.02 } : {}}
            whileTap={!disableAnimation && !isDisabled ? { scale: 0.98 } : {}}
            {...rest}
          >
            <Flex align="center">
              <Icon as={FaWallet} mr={2} />
              {state === "idle" ? (
                children || "Connect Wallet"
              ) : state === "loading" ? (
                <Flex align="center">
                  <Spinner size="sm" mr={2} />
                  {loadingText || "Connecting..."}
                </Flex>
              ) : state === "success" ? (
                <Flex align="center">
                  <Icon as={FaCheck} mr={2} />
                  {successText || "Connected"}
                </Flex>
              ) : (
                <Flex align="center">
                  <Icon as={FaTimes} mr={2} />
                  {errorText || "Connection Failed"}
                </Flex>
              )}
            </Flex>
          </MotionChakraButton>
        </Tooltip>
      );
    }

    // Special button for blockchain transactions
    if (variant === "transaction") {
      return (
        <Tooltip
          label={tooltipText || transactionHash}
          isDisabled={!tooltipText && !transactionHash}
        >
          <MotionChakraButton
            ref={ref}
            display="flex"
            alignItems="center"
            justifyContent="center"
            bg={getButtonBgColor()}
            color={getButtonTextColor()}
            border={getButtonBorder()}
            borderRadius={rounded}
            width={fullWidth ? "100%" : "auto"}
            {...getButtonPadding()}
            fontSize={getButtonFontSize()}
            isDisabled={
              isDisabled || state === "loading" || state === "confirming"
            }
            onClick={handleClick}
            _hover={!isDisabled ? getButtonHoverStyle() : undefined}
            _active={!isDisabled ? { transform: "scale(0.98)" } : undefined}
            position="relative"
            overflow="hidden"
            transition="all 0.2s"
            whileHover={!disableAnimation && !isDisabled ? { scale: 1.02 } : {}}
            whileTap={!disableAnimation && !isDisabled ? { scale: 0.98 } : {}}
            {...rest}
          >
            <Flex align="center">
              {chainIcon && <Box mr={2}>{chainIcon}</Box>}
              {state === "idle" ? (
                <Flex align="center">
                  <Icon as={FaExchangeAlt} mr={2} />
                  {children || "Send Transaction"}
                </Flex>
              ) : state === "loading" ? (
                <Flex align="center">
                  <Spinner size="sm" mr={2} />
                  {loadingText || "Preparing..."}
                </Flex>
              ) : state === "confirming" ? (
                <Flex align="center">
                  <Spinner size="sm" mr={2} />
                  {confirmingText || "Confirming..."}
                </Flex>
              ) : state === "success" ? (
                <Flex align="center">
                  <Icon as={FaCheck} mr={2} />
                  {successText || "Confirmed"}
                </Flex>
              ) : (
                <Flex align="center">
                  <Icon as={FaTimes} mr={2} />
                  {errorText || "Failed"}
                </Flex>
              )}
            </Flex>

            {state === "progress" && (
              <Box
                position="absolute"
                bottom="0"
                left="0"
                width="100%"
                height="4px"
                overflow="hidden"
              >
                <Progress
                  value={progress}
                  size="xs"
                  colorScheme="orange"
                  hasStripe
                  isAnimated
                />
              </Box>
            )}
          </MotionChakraButton>
        </Tooltip>
      );
    }

    // Regular enhanced button with all features
    return (
      <Tooltip label={tooltipText} isDisabled={!tooltipText}>
        <Box
          position="relative"
          width={fullWidth ? "100%" : "auto"}
          style={{ "--pulse-color": getPulseColorRgb() } as React.CSSProperties}
        >
          <MotionChakraButton
            ref={ref}
            display="flex"
            alignItems="center"
            justifyContent="center"
            bg={getButtonBgColor()}
            color={getButtonTextColor()}
            border={getButtonBorder()}
            borderRadius={rounded}
            width="100%"
            {...getButtonPadding()}
            fontSize={getButtonFontSize()}
            isDisabled={isDisabled || state === "loading"}
            onClick={handleClick}
            _hover={!isDisabled ? getButtonHoverStyle() : undefined}
            _active={!isDisabled ? { transform: "scale(0.98)" } : undefined}
            position="relative"
            overflow="hidden"
            transition="all 0.2s"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            variants={
              pulseAnimation && !isDisabled
                ? pulseAnimationVariants
                : !disableAnimation
                ? buttonAnimationVariants
                : undefined
            }
            initial="idle"
            animate={pulseAnimation && !isDisabled ? "pulse" : controls}
            whileHover={!disableAnimation && !isDisabled ? "hover" : undefined}
            whileTap={!disableAnimation && !isDisabled ? "tap" : undefined}
            backdropFilter={glassMorphism ? "blur(10px)" : undefined}
            {...rest}
          >
            {renderButtonContent()}

            {/* Glassmorphism effect */}
            {glassMorphism && (
              <Box
                position="absolute"
                top="0"
                left="0"
                right="0"
                bottom="0"
                backdropFilter="blur(10px)"
                borderRadius={rounded}
                zIndex="-1"
              />
            )}

            {/* Hover overlay for subtle effects */}
            {!disableAnimation && (
              <AnimatePresence>
                {isHovered && !isDisabled && (
                  <MotionBox
                    position="absolute"
                    top="0"
                    left="0"
                    right="0"
                    bottom="0"
                    bg="rgba(255, 255, 255, 0.1)"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    zIndex="1"
                    pointerEvents="none"
                  />
                )}
              </AnimatePresence>
            )}
          </MotionChakraButton>
        </Box>
      </Tooltip>
    );
  }
);

EnhancedButton.displayName = "EnhancedButton";

export default EnhancedButton;
