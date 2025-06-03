import * as React from "react";
import { Link, Icon } from "@chakra-ui/react";
import { ExternalLinkIcon } from "@chakra-ui/icons";

const formatContent = (text: string) => {
  return text.split("\n").map((line, i) => (
    <React.Fragment key={i}>
      {line}
      {i < text.split("\n").length - 1 && <br />}
    </React.Fragment>
  ));
};

// Format links in content
export const formatLinks = (text: string | undefined | null) => {
  // Early exit if input is not a string or is empty
  if (typeof text !== "string" || !text) return null;

  // Process markdown-style links first - format: [text](url)
  const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  let processedText = text;
  let mdMatch: RegExpExecArray | null;

  // Define the type for the replacements
  interface MarkdownReplacement {
    placeholder: string;
    text: string;
    url: string;
  }

  // Initialize with explicit type
  const mdReplacements = [] as MarkdownReplacement[];

  // Replace markdown links with placeholders to avoid conflicts with URL regex
  while ((mdMatch = markdownLinkRegex.exec(text)) !== null) {
    const placeholderText = `__MARKDOWN_LINK_${mdReplacements.length}__`;
    mdReplacements.push({
      placeholder: placeholderText,
      text: mdMatch[1],
      url: mdMatch[2],
    });
    processedText = processedText.replace(mdMatch[0], placeholderText);
  }

  // Now process regular URLs
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = processedText.split(urlRegex);

  // Map the parts, handling both regular URLs and our markdown link placeholders
  return parts.map((part, i) => {
    // Check if this part is a URL
    if (part.match(urlRegex)) {
      return (
        <Link key={i} href={part} isExternal color="blue.500">
          {part} <Icon as={ExternalLinkIcon} mx="2px" fontSize="xs" />
        </Link>
      );
    }

    // Check if this part contains any of our markdown link placeholders
    let result = part;
    for (const replacement of mdReplacements) {
      if (part.includes(replacement.placeholder)) {
        // Replace the placeholder with the actual link component
        const beforePlaceholder = part.substring(
          0,
          part.indexOf(replacement.placeholder)
        );
        const afterPlaceholder = part.substring(
          part.indexOf(replacement.placeholder) +
            replacement.placeholder.length
        );

        return (
          <React.Fragment key={i}>
            {beforePlaceholder && formatContent(beforePlaceholder)}
            <Link href={replacement.url} isExternal color="blue.500">
              {replacement.text}{" "}
              <Icon as={ExternalLinkIcon} mx="2px" fontSize="xs" />
            </Link>
            {afterPlaceholder && formatContent(afterPlaceholder)}
          </React.Fragment>
        );
      }
    }

    // If no replacements were needed, just format the content normally
    return formatContent(result);
  });
};
