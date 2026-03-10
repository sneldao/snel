import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "light",
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  semanticTokens: {
    colors: {
      // Background colors
      "bg.primary": {
        default: "white",
        _dark: "gray.900",
      },
      "bg.secondary": {
        default: "gray.50",
        _dark: "gray.800",
      },
      "bg.tertiary": {
        default: "gray.100",
        _dark: "gray.700",
      },
      // Text colors
      "text.primary": {
        default: "gray.800",
        _dark: "gray.100",
      },
      "text.secondary": {
        default: "gray.600",
        _dark: "gray.300",
      },
      "text.muted": {
        default: "gray.500",
        _dark: "gray.400",
      },
      // Border colors
      "border.default": {
        default: "gray.200",
        _dark: "gray.600",
      },
      "border.hover": {
        default: "gray.300",
        _dark: "gray.500",
      },
      // Brand colors with dark mode variants
      "brand.primary": {
        default: "blue.500",
        _dark: "blue.300",
      },
      "brand.secondary": {
        default: "purple.500",
        _dark: "purple.300",
      },
    },
  },
  styles: {
    global: (props: { colorMode: string }) => ({
      body: {
        bg: props.colorMode === "dark" ? "gray.900" : "white",
        color: props.colorMode === "dark" ? "gray.100" : "gray.800",
      },
    }),
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: "semibold",
        borderRadius: "md",
      },
      variants: {
        solid: (props: { colorMode: string }) => ({
          bg: "blue.500",
          color: "white",
          _hover: {
            bg: "blue.600",
            _dark: {
              bg: "blue.400",
            },
          },
          _dark: {
            bg: "blue.300",
            color: "gray.900",
            _hover: {
              bg: "blue.400",
            },
          },
        }),
        ghost: (props: { colorMode: string }) => ({
          _hover: {
            bg: props.colorMode === "dark" ? "whiteAlpha.200" : "gray.100",
          },
        }),
        outline: (props: { colorMode: string }) => ({
          borderColor: props.colorMode === "dark" ? "gray.500" : "gray.300",
          _hover: {
            bg: props.colorMode === "dark" ? "whiteAlpha.100" : "gray.50",
          },
        }),
      },
    },
    Input: {
      variants: {
        filled: (props: { colorMode: string }) => ({
          field: {
            bg: props.colorMode === "dark" ? "gray.800" : "gray.50",
            borderColor: props.colorMode === "dark" ? "gray.600" : "gray.200",
            _hover: {
              bg: props.colorMode === "dark" ? "gray.700" : "gray.100",
            },
            _focus: {
              bg: props.colorMode === "dark" ? "gray.800" : "white",
              borderColor: "blue.500",
            },
          },
        }),
      },
      defaultProps: {
        variant: "filled",
      },
    },
    Card: {
      baseStyle: (props: { colorMode: string }) => ({
        container: {
          bg: props.colorMode === "dark" ? "gray.800" : "white",
          borderColor: props.colorMode === "dark" ? "gray.600" : "gray.200",
          borderWidth: "1px",
        },
      }),
    },
    Modal: {
      baseStyle: (props: { colorMode: string }) => ({
        dialog: {
          bg: props.colorMode === "dark" ? "gray.800" : "white",
        },
        header: {
          borderBottomColor: props.colorMode === "dark" ? "gray.600" : "gray.200",
        },
        footer: {
          borderTopColor: props.colorMode === "dark" ? "gray.600" : "gray.200",
        },
      }),
    },
    Menu: {
      baseStyle: (props: { colorMode: string }) => ({
        list: {
          bg: props.colorMode === "dark" ? "gray.800" : "white",
          borderColor: props.colorMode === "dark" ? "gray.600" : "gray.200",
        },
        item: {
          bg: "transparent",
          _hover: {
            bg: props.colorMode === "dark" ? "gray.700" : "gray.100",
          },
          _focus: {
            bg: props.colorMode === "dark" ? "gray.700" : "gray.100",
          },
        },
      }),
    },
    Tabs: {
      variants: {
        line: (props: { colorMode: string }) => ({
          tab: {
            _selected: {
              color: "blue.500",
              borderColor: "blue.500",
            },
          },
        }),
      },
    },
  },
  colors: {
    gray: {
      50: "#F7FAFC",
      100: "#EDF2F7",
      200: "#E2E8F0",
      300: "#CBD5E0",
      400: "#A0AEC0",
      500: "#718096",
      600: "#4A5568",
      700: "#2D3748",
      800: "#1A202C",
      900: "#171923",
    },
  },
});

export default theme;
