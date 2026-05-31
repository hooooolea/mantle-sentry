// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title MantleSentryAnchor
/// @notice On-chain anchor for MantleSentry daily AI summaries.
///         Stores keccak256 hashes of daily reports — proves existence
///         and integrity without storing full text on-chain.
contract MantleSentryAnchor {

    struct Summary {
        bytes32 hash;       // keccak256(summary_text)
        uint256 timestamp;  // block.timestamp
        string  date;       // "YYYY-MM-DD"
    }

    mapping(string => Summary) private _summaries;  // date → Summary
    string[] private _dates;

    address public owner;

    event SummaryAnchored(
        string  indexed date,
        bytes32 indexed hash,
        uint256         timestamp,
        uint256         summaryCount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Store a daily summary hash. Overwrites if date already exists.
    /// @param date  "YYYY-MM-DD"
    /// @param hash  keccak256(summary_text)
    function anchorSummary(string calldata date, bytes32 hash) external onlyOwner {
        require(bytes(date).length > 0, "empty date");
        require(hash != bytes32(0), "zero hash");

        if (_summaries[date].timestamp == 0) {
            _dates.push(date);
        }

        _summaries[date] = Summary({
            hash:      hash,
            timestamp: block.timestamp,
            date:      date
        });

        emit SummaryAnchored(date, hash, block.timestamp, _dates.length);
    }

    /// @notice Get summary by date.
    function getSummary(string calldata date) external view returns (
        bytes32 hash, uint256 timestamp
    ) {
        Summary memory s = _summaries[date];
        return (s.hash, s.timestamp);
    }

    /// @notice Total anchored summaries.
    function summaryCount() external view returns (uint256) {
        return _dates.length;
    }

    /// @notice Get date by index.
    function dateAt(uint256 index) external view returns (string memory) {
        require(index < _dates.length, "out of bounds");
        return _dates[index];
    }
}
